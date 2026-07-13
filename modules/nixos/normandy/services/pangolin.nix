{ config, pkgs, lib, ... }:

let
  hosts = import ../../shared/lib/hosts.nix;

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

in
{
  sops.secrets."pangolin/acme_email" = {};

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
      ACME_EMAIL=$(cat ${config.sops.secrets."pangolin/acme_email".path})
      ${pkgs.gnused}/bin/sed \
        "s|__SERVER_SECRET__|$SERVER_SECRET|" \
        ${../../../config/pangolin/config.yml.tmpl} \
        > /persist/pangolin/config/config.yml
      ${pkgs.gnused}/bin/sed \
        "s|__ACME_EMAIL__|$ACME_EMAIL|g" \
        ${../../../config/pangolin/traefik-static.yml.tmpl} \
        > /persist/pangolin/config/traefik/traefik_config.yml
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
      install -m 0644 ${../../../config/resources/ishimura-favicon.png} \
        /persist/pangolin/errors/ishimura-favicon.png
      ${pkgs.gnused}/bin/sed \
        -e "s|__CROWDSEC_TRAEFIK_API_KEY__|$CROWDSEC_KEY|g" \
        -e "s|__ISHIMURA_IP__|${hosts.ishimura.tailnet}|g" \
        -e "s|__NOSTROMO_IP__|${hosts.nostromo.tailnet}|g" \
        -e "s|__DOMAIN__|ishimura.lol|g" \
        -e "s|__DASHBOARD_HOST__|pangolin.ishimura.lol|g" \
        ${../../../config/pangolin/traefik-dynamic.yml.tmpl} \
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
