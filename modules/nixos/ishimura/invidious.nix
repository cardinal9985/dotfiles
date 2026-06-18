{ config, pkgs, ... }:

{
  # Pre-declare user+group so sops can resolve owner at eval time.
  # services.invidious also declares this user; NixOS merges cleanly.
  users.users.invidious = {
    isSystemUser = true;
    group = "invidious";
  };
  users.groups.invidious = {};

  sops.secrets."invidious/hmac_key"      = { mode = "0400"; };
  sops.secrets."invidious/companion_key" = { mode = "0400"; };

  # services.invidious's start script merges hmacKeyFile contents into the
  # runtime config via jq, so the file must be JSON. We also fold in the
  # companion config + companion_key here as one extra "settings overlay"
  # because the public services.invidious settings block doesn't support
  # secret interpolation cleanly.
  sops.templates."invidious-extra.json" = {
    content = ''
      {
        "hmac_key": "${config.sops.placeholder."invidious/hmac_key"}",
        "invidious_companion_key": "${config.sops.placeholder."invidious/companion_key"}",
        "invidious_companion": [
          {
            "private_url": "http://127.0.0.1:8282/companion",
            "public_url":  "https://invidious.ishimura.lol/companion"
          }
        ]
      }
    '';
    owner = "invidious";
  };

  # Companion env file. Companion's SERVER_SECRET_KEY must match Invidious's
  # invidious_companion_key for HMAC signatures to validate.
  # PO token generation disabled: YouTube currently blocks PO-token validation
  # attempts from residential server IPs (the companion's automatic method
  # exhausts retries). Without PO token, video playback works for most
  # non-age-restricted content. Re-enable with cookies later for full coverage.
  sops.templates."invidious-companion.env" = {
    content = ''
      SERVER_SECRET_KEY=${config.sops.placeholder."invidious/companion_key"}
      INVIDIOUS_DOMAIN=invidious.ishimura.lol
      PORT=8282
      JOBS_YOUTUBE_SESSION_PO_TOKEN_ENABLED=false
      # Keep default /companion base path. Invidious's private_url has
      # /companion suffix to match; Pangolin no longer strips the prefix.
    '';
  };

  services.invidious = {
    enable = true;
    domain = "invidious.ishimura.lol";
    port = 3939;
    nginx.enable = false;
    hmacKeyFile = config.sops.templates."invidious-extra.json".path;
  };

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/postgresql"; user = "postgres"; group = "postgres"; mode = "0700"; }
  ];

  # Same DNS-conflict workaround pelican/tdarr use: AGH holds udp/53 on every
  # interface so aardvark-dns can't start for the default podman network.
  systemd.services.create-invidious-companion-network = {
    description = "Create invidious-companion podman network (no DNS)";
    wantedBy = [ "podman-invidious-companion.service" ];
    before   = [ "podman-invidious-companion.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists invidious-companion-net || \
        ${pkgs.podman}/bin/podman network create --disable-dns invidious-companion-net
    '';
  };

  virtualisation.oci-containers.containers.invidious-companion = {
    image = "quay.io/invidious/invidious-companion:latest";
    environmentFiles = [ config.sops.templates."invidious-companion.env".path ];
    ports = [ "127.0.0.1:8282:8282" ];
    extraOptions = [ "--network=invidious-companion-net" ];
  };

  systemd.services.podman-invidious-companion.after = [ "create-invidious-companion-network.service" ];
}
