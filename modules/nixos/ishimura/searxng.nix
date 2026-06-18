{ config, pkgs, ... }:

let
  tailnetIP = "100.92.76.121";
  # Static IPs on a dedicated podman network. AGH holds udp/53 so we run with
  # --disable-dns and address Valkey by IP rather than hostname.
  valkeyIP  = "10.89.70.10";
  searxngIP = "10.89.70.11";
in
{
  # Activation script (vs systemd.tmpfiles) so the dirs exist before podman
  # tries to bind-mount them. tmpfiles raced the container startup on first
  # deploy and pushed the unit past its restart limit.
  system.activationScripts.searxng-dirs = ''
    install -d -m 0755 -o 977 -g 977   /persist/searxng
    install -d -m 0750 -o 977 -g 977   /persist/searxng/data
    install -d -m 0750 -o 999 -g 1000  /persist/searxng/valkey
  '';

  environment.persistence."/persist".directories = [
    "/persist/searxng"
  ];

  systemd.services.create-searxng-network = {
    description = "Create searxng podman network (no DNS, static subnet)";
    wantedBy = [ "podman-searxng.service" "podman-searxng-valkey.service" ];
    before   = [ "podman-searxng.service" "podman-searxng-valkey.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists searxng-net || \
        ${pkgs.podman}/bin/podman network create \
          --disable-dns \
          --subnet=10.89.70.0/24 \
          searxng-net
    '';
  };

  # settings.yml lives in the Nix store (rendered by sops so the secret_key
  # is inlined at activation time). Mount read-only into the container; the
  # searxng user reads it during startup.
  sops.templates."searxng-settings.yml" = {
    mode = "0444";
    content = ''
      use_default_settings: true
      general:
        instance_name: "USG Ishimura"
        privacypolicy_url: false
        donation_url: false
        contact_url: false
        enable_metrics: true
      server:
        port: 8080
        bind_address: "0.0.0.0"
        base_url: https://search.ishimura.lol/
        secret_key: "${config.sops.placeholder."searxng/secret_key"}"
        limiter: true
        image_proxy: true
        method: "POST"
        public_instance: false
        default_http_headers:
          X-Content-Type-Options: nosniff
          X-Download-Options: noopen
          X-Robots-Tag: noindex, nofollow
          Referrer-Policy: no-referrer
      valkey:
        url: valkey://${valkeyIP}:6379/0
      search:
        safe_search: 0
        autocomplete: duckduckgo
        formats:
          - html
          - json
      ui:
        static_use_hash: true
        default_theme: simple
        theme_args:
          simple_style: dark
        infinite_scroll: false
      enabled_plugins:
        - 'Hash plugin'
        - 'Search on category select'
        - 'Self Informations'
        - 'Tracker URL remover'
        - 'Unit converter plugin'
    '';
  };

  virtualisation.oci-containers.containers = {
    searxng-valkey = {
      image = "docker.io/valkey/valkey:8-alpine";
      cmd = [
        "valkey-server"
        "--save" "30" "1"
        "--loglevel" "warning"
      ];
      volumes = [
        "/persist/searxng/valkey:/data"
      ];
      extraOptions = [
        "--network=searxng-net"
        "--ip=${valkeyIP}"
      ];
    };

    searxng = {
      image = "docker.io/searxng/searxng:latest";
      environment = {
        TZ = "America/New_York";
      };
      volumes = [
        "${config.sops.templates."searxng-settings.yml".path}:/etc/searxng/settings.yml:ro"
        "/persist/searxng/data:/var/cache/searxng"
      ];
      ports = [ "${tailnetIP}:8888:8080" ];
      extraOptions = [
        "--network=searxng-net"
        "--ip=${searxngIP}"
      ];
      dependsOn = [ "searxng-valkey" ];
    };
  };

  systemd.services.podman-searxng.after        = [ "create-searxng-network.service" ];
  systemd.services.podman-searxng-valkey.after = [ "create-searxng-network.service" ];
}
