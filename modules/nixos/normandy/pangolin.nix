{ config, pkgs, lib, ... }:

let
  domain         = "ishimura.lol";
  dashboardHost  = "pangolin.${domain}";
  acmeEmail      = "fanatical.despise915@simplelogin.com";

  crowdsecPluginSrc = pkgs.fetchFromGitHub {
    owner = "maxlerebourg";
    repo  = "crowdsec-bouncer-traefik-plugin";
    rev   = "v1.4.6";
    hash  = "sha256-r4T+0mT9YHmfu/nFhvjpyiz/Z7ViF3yLJKmOuwbnK60=";
  };

  configYamlTemplate = pkgs.writeText "pangolin-config.yml.tmpl" ''
    app:
      dashboard_url: "https://${dashboardHost}"
      base_domain: "${domain}"
      log_level: "info"
      save_logs: false
    server:
      external_port: 3000
      internal_port: 3001
      next_port: 3002
      internal_hostname: pangolin
      session_cookie_name: pangolin
      resource_session_cookie_name: pangolin_resource
      secret: __SERVER_SECRET__
      cors:
        origins: ["https://${dashboardHost}"]
    domains:
      domain1:
        base_domain: "${domain}"
        cert_resolver: letsencrypt
    gerbil:
      start_port: 51820
      base_endpoint: "${dashboardHost}"
      use_subdomain: false
      block_size: 24
      site_block_size: 30
      subnet_group: 100.89.137.0/20
    flags:
      require_email_verification: false
      disable_signup_without_invite: true
      disable_user_create_org: false
      allow_raw_resources: true
  '';

  traefikDynamicConfig = pkgs.writeText "dynamic_config.yml" ''
    http:
      middlewares:
        crowdsec:
          plugin:
            crowdsec:
              enabled: true
              logLevel: INFO
              updateIntervalSeconds: 30
              defaultDecisionSeconds: 60
              crowdsecMode: live
              crowdsecLapiHost: 127.0.0.1:8081
              crowdsecLapiScheme: http
              crowdsecLapiKey: __CROWDSEC_TRAEFIK_API_KEY__
              banHTMLFilePath: /etc/traefik/ban.html
        tailnet-only:
          ipAllowList:
            sourceRange:
              - 100.64.0.0/10
      routers:
        next-router:
          rule: "Host(`${dashboardHost}`)"
          service: next-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          middlewares:
            - tailnet-only
        api-router:
          rule: "Host(`${dashboardHost}`) && PathPrefix(`/api/v1`)"
          service: api-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          middlewares:
            - tailnet-only
        auth-admin-router:
          rule: "Host(`auth.${domain}`) && PathPrefix(`/admin`)"
          service: auth-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          priority: 20
          middlewares:
            - tailnet-only
        auth-router:
          rule: "Host(`auth.${domain}`)"
          service: auth-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          priority: 10
      services:
        next-service:
          loadBalancer:
            servers:
              - url: "http://127.0.0.1:3002"
        api-service:
          loadBalancer:
            servers:
              - url: "http://127.0.0.1:3000"
        auth-service:
          loadBalancer:
            servers:
              - url: "http://127.0.0.1:3030"
  '';

  traefikStaticConfig = pkgs.writeText "traefik_config.yml" ''
    api:
      insecure: true
      dashboard: true
    accessLog:
      filePath: "/var/log/traefik/access.log"
      format: json
    experimental:
      localPlugins:
        crowdsec:
          moduleName: github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin
    providers:
      http:
        endpoint: "http://127.0.0.1:3001/api/v1/traefik-config"
        pollInterval: "5s"
      file:
        directory: "/etc/traefik/dynamic"
        watch: true
    entryPoints:
      web:
        address: ":80"
        http:
          redirections:
            entryPoint:
              to: websecure
              scheme: https
      websecure:
        address: ":443"
        transport:
          respondingTimeouts:
            readTimeout: "30m"
        http3: {}
        http:
          tls:
            certResolver: letsencrypt
          middlewares:
            - crowdsec@file
    certificatesResolvers:
      letsencrypt:
        acme:
          httpChallenge:
            entryPoint: web
          email: ${acmeEmail}
          storage: "/letsencrypt/acme.json"
          caServer: "https://acme-v02.api.letsencrypt.org/directory"
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/pangolin                       0750 root root -"
    "d /persist/pangolin/config                0750 root root -"
    "d /persist/pangolin/config/traefik        0750 root root -"
    "d /persist/pangolin/config/traefik/dynamic 0750 root root -"
    "d /persist/pangolin/config/traefik/logs   0750 root root -"
    "d /persist/pangolin/config/letsencrypt    0750 root root -"
  ];

  systemd.services.pangolin-render-config = {
    description = "Render Pangolin configs from templates + sops secrets";
    wantedBy = [ "podman-pangolin.service" ];
    before   = [ "podman-pangolin.service" "podman-gerbil.service" "podman-traefik.service" ];
    after    = [ "sops-nix.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail
      SERVER_SECRET=$(cat ${config.sops.secrets."pangolin/server_secret".path})
      CROWDSEC_KEY=$(cat ${config.sops.secrets."crowdsec/traefik_bouncer_api_key".path})
      ${pkgs.gnused}/bin/sed \
        "s|__SERVER_SECRET__|$SERVER_SECRET|" \
        ${configYamlTemplate} \
        > /persist/pangolin/config/config.yml
      install -m 0644 ${traefikStaticConfig} \
        /persist/pangolin/config/traefik/traefik_config.yml
      install -m 0644 ${../../../config/pangolin/ban.html} \
        /persist/pangolin/config/traefik/ban.html
      ${pkgs.gnused}/bin/sed \
        "s|__CROWDSEC_TRAEFIK_API_KEY__|$CROWDSEC_KEY|" \
        ${traefikDynamicConfig} \
        > /persist/pangolin/config/traefik/dynamic/dynamic_config.yml
    '';
  };

  virtualisation.oci-containers.containers = {
    pangolin = {
      image = "docker.io/fosrl/pangolin:latest";
      volumes = [ "/persist/pangolin/config:/app/config" ];
      ports = [
        "127.0.0.1:3000:3000"
        "127.0.0.1:3001:3001"
        "127.0.0.1:3002:3002"
      ];
      extraOptions = [ "--network=pangolin" ];
    };

    gerbil = {
      image = "docker.io/fosrl/gerbil:latest";
      dependsOn = [ "pangolin" ];
      cmd = [
        "--reachableAt=http://host.containers.internal:3004"
        "--generateAndSaveKeyTo=/var/config/key"
        "--remoteConfig=http://127.0.0.1:3001/api/v1/"
      ];
      volumes = [ "/persist/pangolin/config:/var/config" ];
      extraOptions = [
        "--network=host"
        "--cap-add=NET_ADMIN"
        "--cap-add=SYS_MODULE"
      ];
    };

    traefik = {
      image = "docker.io/traefik:v3.6";
      dependsOn = [ "pangolin" "gerbil" ];
      cmd = [ "--configFile=/etc/traefik/traefik_config.yml" ];
      volumes = [
        "/persist/pangolin/config/traefik:/etc/traefik:ro"
        "/persist/pangolin/config/letsencrypt:/letsencrypt"
        "/persist/pangolin/config/traefik/logs:/var/log/traefik"
        "${crowdsecPluginSrc}:/plugins-local/src/github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin:ro"
      ];
      extraOptions = [ "--network=container:gerbil" ];
    };
  };

  systemd.services.create-pangolin-network = {
    description = "Create pangolin podman network";
    wantedBy = [ "podman-pangolin.service" "podman-gerbil.service" ];
    before   = [ "podman-pangolin.service" "podman-gerbil.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists pangolin || \
        ${pkgs.podman}/bin/podman network create pangolin
    '';
  };
}
