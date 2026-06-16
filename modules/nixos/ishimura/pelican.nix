{ config, pkgs, ... }:

let
  pelicanHost = "pelican.ishimura.lol";
in
{
  # Pelican container runs as www-data (UID/GID 33 in the standard PHP base
   # image). Bind-mounted volumes need that ownership or the entrypoint can't
   # write .env / logs / database files.
  systemd.tmpfiles.rules = [
    "d /persist/pelican       0755 33 33 -"
    "d /persist/pelican/data  0755 33 33 -"
    "d /persist/pelican/logs  0755 33 33 -"
  ];

  # AdGuard Home holds udp/53 on every interface including podman's default
  # bridge gateway 10.88.0.1, so aardvark-dns can't start for the default
  # podman network. Create a dedicated network with DNS disabled - Pelican
  # uses the host's resolv.conf for any external lookups, no podman DNS
  # needed inside a single-container deployment.
  systemd.services.create-pelican-network = {
    description = "Create pelican podman network (no DNS)";
    wantedBy = [ "podman-pelican.service" ];
    before   = [ "podman-pelican.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists pelican-net || \
        ${pkgs.podman}/bin/podman network create --disable-dns pelican-net
    '';
  };

  # Pelican stores APP_KEY in /pelican-data/.env on first run. Sopsing it
  # ourselves guarantees the key survives a /persist wipe. Generate with:
  #   openssl rand -base64 32 | sed 's|^|base64:|'
  sops.templates."pelican.env" = {
    content = ''
      APP_URL=https://${pelicanHost}
      APP_KEY=${config.sops.placeholder."pelican/app_key"}
      APP_ENV=production
      APP_DEBUG=false
      APP_TIMEZONE=UTC
      ADMIN_EMAIL=fanatical.despise915@simplelogin.com
      XDG_DATA_HOME=/pelican-data
      BEHIND_PROXY=true
    '';
  };

  virtualisation.oci-containers.containers.pelican = {
    image = "ghcr.io/pelican-dev/panel@sha256:e22f847fc727b1af287222c3294046afc5a76555e9bd2eef29bc02052bf45354";
    environmentFiles = [ config.sops.templates."pelican.env".path ];
    volumes = [
      "/persist/pelican/data:/pelican-data"
      "/persist/pelican/logs:/var/www/html/storage/logs"
    ];
    ports = [ "0.0.0.0:8801:80" ];
    extraOptions = [ "--network=pelican-net" ];
  };

  systemd.services.podman-pelican.after = [ "create-pelican-network.service" ];
}
