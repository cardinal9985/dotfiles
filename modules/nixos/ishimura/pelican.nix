{ config, pkgs, ... }:

let
  pelicanHost = "pelican.ishimura.lol";
in
{
  systemd.tmpfiles.rules = [
    "d /persist/pelican       0755 82 82 -"
    "d /persist/pelican/data  0755 82 82 -"
    "d /persist/pelican/logs  0755 82 82 -"
  ];

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
    extraOptions = [
      "--network=pelican-net"
      "--cap-add=NET_BIND_SERVICE"
    ];
  };

  systemd.services.podman-pelican.after = [ "create-pelican-network.service" ];
}
