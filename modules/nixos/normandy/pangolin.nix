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

  rewriteBodyPluginSrc = pkgs.fetchFromGitHub {
    owner = "packruler";
    repo  = "rewrite-body";
    rev   = "v1.2.0";
    hash  = "sha256-dl+FYEoUMYlodg9xp8e/RQAt0wuBwLICyVwgKR+/1ZQ=";
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
        error-pages:
          errors:
            status:
              - "403"
              - "404"
            service: errors-service
            query: /{status}.html
        noindex-headers:
          headers:
            customResponseHeaders:
              X-Robots-Tag: "noindex, nofollow, noarchive, nosnippet, noimageindex"
        # Inject the stylesheet only on Anubis-served pages. auth-router
        # proxies BOTH Anubis challenge pages and voidauth's Angular SPA
        # responses, so matching a universal HTML anchor like </head>
        # tears up voidauth's strict-dynamic + sha256 CSP hashes and the
        # SPA refuses to bootstrap.
        #
        # The anchor here, <script id="anubis_version", appears on every
        # Anubis page (challenge AND error) and on zero voidauth pages,
        # so this rewrite is a no-op on voidauth responses and the CSP
        # hashes survive intact.
        anubis-theme:
          plugin:
            rewriteBody:
              lastModified: true
              rewrites:
                - regex: '<script id="anubis_version"'
                  replacement: '<link rel="stylesheet" href="/anubis-theme.css"><script id="anubis_version"'
        voidauth-forwardauth:
          forwardAuth:
            address: "http://127.0.0.1:3030/api/authz/forward-auth"
            trustForwardHeader: true
            authResponseHeaders:
              - Remote-User
              - Remote-Name
              - Remote-Email
              - Remote-Groups
        rewrite-jellyfin-health:
          replacePath:
            path: "/health"
        rewrite-scrutiny-health:
          replacePath:
            path: "/api/health"
        rewrite-ntfy-health:
          replacePath:
            path: "/v1/health"
        rewrite-voidauth-health:
          replacePath:
            path: "/oidc/jwks"
        rewrite-tdarr-health:
          replacePath:
            path: "/api/v2/status"
        rewrite-adguard-health:
          replacePath:
            path: "/login.html"
        rewrite-grafana-health:
          replacePath:
            path: "/api/health"
        rewrite-prometheus-health:
          replacePath:
            path: "/-/healthy"
        rewrite-pelican-health:
          replacePath:
            path: "/up"
        rewrite-invidious-health:
          replacePath:
            path: "/api/v1/stats"
        strip-companion-prefix:
          stripPrefix:
            prefixes:
              - /companion
        rewrite-approval-required:
          replacePath:
            path: "/approval_required.html"
      routers:
        robots-router:
          rule: "Path(`/robots.txt`)"
          service: errors-service
          entryPoints:
            - websecure
          priority: 1000
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          middlewares:
            - noindex-headers
        next-router:
          rule: "Host(`${dashboardHost}`)"
          service: next-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        api-router:
          rule: "Host(`${dashboardHost}`) && PathPrefix(`/api/v1`)"
          service: api-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        auth-approval-router:
          rule: "Host(`auth.${domain}`) && Path(`/approval_required`)"
          service: errors-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 30
          middlewares:
            - noindex-headers
            - rewrite-approval-required
        auth-admin-router:
          rule: "Host(`auth.${domain}`) && PathPrefix(`/admin`)"
          service: auth-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          priority: 20
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        anubis-theme-css-router:
          rule: "(Host(`auth.${domain}`) || Host(`${domain}`)) && Path(`/anubis-theme.css`)"
          service: errors-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          priority: 100
          middlewares:
            - noindex-headers
        ishimura-banner-png-router:
          rule: "HostRegexp(`^.+\\.${domain}$`) && Path(`/ishimura-banner.png`)"
          service: errors-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 100
          middlewares:
            - noindex-headers
        auth-router:
          rule: "Host(`auth.${domain}`)"
          service: auth-service
          entryPoints:
            - websecure
          tls:
            certResolver: letsencrypt
          priority: 10
          middlewares:
            - noindex-headers
            - anubis-theme
            - error-pages
        homepage-health-jellyfin-router:
          rule: "Host(`${domain}`) && Path(`/health/jellyfin`)"
          service: ishimura-jellyfin-health-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-jellyfin-health
        homepage-health-scrutiny-router:
          rule: "Host(`${domain}`) && Path(`/health/scrutiny`)"
          service: scrutiny-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-scrutiny-health
        homepage-health-ntfy-router:
          rule: "Host(`${domain}`) && Path(`/health/ntfy`)"
          service: ntfy-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-ntfy-health
        homepage-health-tdarr-router:
          rule: "Host(`${domain}`) && Path(`/health/tdarr`)"
          service: tdarr-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-tdarr-health
        homepage-health-voidauth-router:
          rule: "Host(`${domain}`) && Path(`/health/voidauth`)"
          service: auth-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-voidauth-health
        homepage-health-adguard-router:
          rule: "Host(`${domain}`) && Path(`/health/adguard`)"
          service: adguard-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-adguard-health
        homepage-health-grafana-router:
          rule: "Host(`${domain}`) && Path(`/health/grafana`)"
          service: grafana-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-grafana-health
        homepage-health-invidious-router:
          rule: "Host(`${domain}`) && Path(`/health/invidious`)"
          service: invidious-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-invidious-health
        homepage-health-pelican-router:
          rule: "Host(`${domain}`) && Path(`/health/pelican`)"
          service: pelican-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-pelican-health
        homepage-health-prometheus-router:
          rule: "Host(`${domain}`) && Path(`/health/prometheus`)"
          service: prometheus-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - rewrite-prometheus-health
        homepage-admin-router:
          rule: "Host(`${domain}`) && PathPrefix(`/admin`)"
          service: homepage-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 20
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        homepage-router:
          rule: "Host(`${domain}`)"
          service: homepage-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 5
          middlewares:
            - noindex-headers
            - voidauth-forwardauth
            - error-pages
        scrutiny-router:
          rule: "Host(`scrutiny.${domain}`)"
          service: scrutiny-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        tdarr-router:
          rule: "Host(`tdarr.${domain}`)"
          service: tdarr-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        ntfy-router:
          rule: "Host(`ntfy.${domain}`)"
          service: ntfy-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        adguard-router:
          rule: "Host(`adguard.${domain}`)"
          service: adguard-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        grafana-router:
          rule: "Host(`grafana.${domain}`)"
          service: grafana-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        prometheus-router:
          rule: "Host(`prometheus.${domain}`)"
          service: prometheus-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - error-pages
            - tailnet-only
        jellyfin-router:
          rule: "Host(`jellyfin.${domain}`)"
          service: jellyfin-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
        invidious-companion-router:
          rule: "Host(`invidious.${domain}`) && PathPrefix(`/companion`)"
          service: invidious-companion-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 50
          middlewares:
            - noindex-headers
            - tailnet-only
            - strip-companion-prefix
        invidious-router:
          rule: "Host(`invidious.${domain}`)"
          service: invidious-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
            - tailnet-only
        pelican-router:
          rule: "Host(`pelican.${domain}`)"
          service: pelican-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
        wings-router:
          rule: "Host(`wings.${domain}`)"
          service: wings-service
          entryPoints:
            - websecure
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          priority: 10
          middlewares:
            - noindex-headers
        catchall-router:
          rule: 'HostRegexp(`^.+\.${builtins.replaceStrings ["."] ["\\."] domain}$`)'
          service: errors-service
          entryPoints:
            - websecure
          priority: 1
          tls:
            certResolver: porkbun
            domains:
              - main: "${domain}"
                sans:
                  - "*.${domain}"
          middlewares:
            - noindex-headers
            - error-pages
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
              - url: "http://127.0.0.1:8923"
        errors-service:
          loadBalancer:
            servers:
              - url: "http://127.0.0.1:8085"
        homepage-service:
          loadBalancer:
            servers:
              - url: "http://127.0.0.1:8086"
        ishimura-jellyfin-health-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:8096"
        jellyfin-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:8096"
        pelican-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:8801"
        invidious-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:3939"
        invidious-companion-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:8282"
        wings-service:
          loadBalancer:
            servers:
              - url: "http://100.107.103.76:8080"
        scrutiny-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:47890"
        ntfy-service:
          loadBalancer:
            servers:
              - url: "http://127.0.0.1:8080"
        tdarr-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:8265"
        adguard-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:3000"
        grafana-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:3001"
        prometheus-service:
          loadBalancer:
            servers:
              - url: "http://100.92.76.121:9090"
  '';

  traefikStaticConfig = pkgs.writeText "traefik_config.yml" ''
    accessLog:
      filePath: "/var/log/traefik/access.log"
      format: json
    experimental:
      localPlugins:
        crowdsec:
          moduleName: github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin
        rewriteBody:
          moduleName: github.com/packruler/rewrite-body
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
      # Raw UDP entrypoints for game-server traffic. Pangolin's "raw resource"
      # admin UI pushes a matching TCP/UDP router via the HTTP provider once
      # the resource is defined. Naming convention is protocol-port.
      udp-42420:
        address: ":42420/udp"
    certificatesResolvers:
      letsencrypt:
        acme:
          httpChallenge:
            entryPoint: web
          email: ${acmeEmail}
          storage: "/letsencrypt/acme.json"
          caServer: "https://acme-v02.api.letsencrypt.org/directory"
      porkbun:
        acme:
          dnsChallenge:
            provider: porkbun
            resolvers:
              - "1.1.1.1:53"
              - "8.8.8.8:53"
          email: ${acmeEmail}
          storage: "/letsencrypt/porkbun.json"
          caServer: "https://acme-v02.api.letsencrypt.org/directory"
  '';
in
{
  sops.templates."porkbun.env" = {
    content = ''
      PORKBUN_API_KEY=${config.sops.placeholder."porkbun/api_key"}
      PORKBUN_SECRET_API_KEY=${config.sops.placeholder."porkbun/secret_api_key"}
    '';
  };

  systemd.tmpfiles.rules = [
    "d /persist/pangolin                       0750 root root -"
    "d /persist/pangolin/config                0750 root root -"
    "d /persist/pangolin/config/traefik        0750 root root -"
    "d /persist/pangolin/config/traefik/dynamic 0750 root root -"
    "d /persist/pangolin/config/traefik/logs   0750 root root -"
    "d /persist/pangolin/config/letsencrypt    0750 root root -"
    "d /persist/pangolin/errors                0755 root root -"
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
      install -m 0644 ${../../../config/pangolin/403.html} \
        /persist/pangolin/errors/403.html
      install -m 0644 ${../../../config/pangolin/404.html} \
        /persist/pangolin/errors/404.html
      install -m 0644 ${../../../config/pangolin/approval_required.html} \
        /persist/pangolin/errors/approval_required.html
      install -m 0644 ${../../../config/pangolin/robots.txt} \
        /persist/pangolin/errors/robots.txt
      install -m 0644 ${../../../config/pangolin/anubis-theme.css} \
        /persist/pangolin/errors/anubis-theme.css
      install -m 0644 ${../../../config/pangolin/ishimura-banner.png} \
        /persist/pangolin/errors/ishimura-banner.png
      ${pkgs.gnused}/bin/sed \
        "s|__CROWDSEC_TRAEFIK_API_KEY__|$CROWDSEC_KEY|" \
        ${traefikDynamicConfig} \
        > /persist/pangolin/config/traefik/dynamic/dynamic_config.yml
    '';
  };

  virtualisation.oci-containers.containers = {
    pangolin = {
      image = "docker.io/fosrl/pangolin@sha256:894dcb2c684f27103adf1a26406b48c641d1e7e32eeda2fe2c7b9a0372322bf1";
      volumes = [ "/persist/pangolin/config:/app/config" ];
      ports = [
        "127.0.0.1:3000:3000"
        "127.0.0.1:3001:3001"
        "127.0.0.1:3002:3002"
      ];
      extraOptions = [ "--network=pangolin" ];
    };

    gerbil = {
      image = "docker.io/fosrl/gerbil@sha256:4e0f14b60098207db9ecb574de06ef91a3cfe8b2494019c111d126881a94ae04";
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

    errorpages = {
      image = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
      cmd = [ "httpd" "-f" "-p" "80" "-h" "/www" ];
      volumes = [ "/persist/pangolin/errors:/www:ro" ];
      ports = [ "127.0.0.1:8085:80" ];
      extraOptions = [ "--network=pangolin" ];
    };

    traefik = {
      image = "docker.io/traefik@sha256:2ffe22bff6ac72572a3f6a06c4c5730dd7235bc1cc77a3bd872479827b3fae96";
      dependsOn = [ "pangolin" "gerbil" ];
      cmd = [ "--configFile=/etc/traefik/traefik_config.yml" ];
      environmentFiles = [ config.sops.templates."porkbun.env".path ];
      volumes = [
        "/persist/pangolin/config/traefik:/etc/traefik:ro"
        "/persist/pangolin/config/letsencrypt:/letsencrypt"
        "/persist/pangolin/config/traefik/logs:/var/log/traefik"
        "${crowdsecPluginSrc}:/plugins-local/src/github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin:ro"
        "${rewriteBodyPluginSrc}:/plugins-local/src/github.com/packruler/rewrite-body:ro"
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
