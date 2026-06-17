{ config, pkgs, ... }:

let
  wingsVersion = "1.0.0-beta25";
  wings = pkgs.stdenv.mkDerivation {
    pname = "pelican-wings";
    version = wingsVersion;
    src = pkgs.fetchurl {
      url = "https://github.com/pelican-dev/wings/releases/download/v${wingsVersion}/wings_linux_amd64";
      sha256 = "174kq5lv5f6q7r8i0hbqqimcwqv3ckgxhrqnw4wqsidl5hqgicag";
    };
    dontUnpack = true;
    nativeBuildInputs = [ pkgs.autoPatchelfHook ];
    buildInputs = [ pkgs.stdenv.cc.cc.lib ];
    installPhase = ''
      install -Dm755 $src $out/bin/wings
    '';
  };
in
{
  # Wings tries to `useradd pelican` on startup; NixOS doesn't ship useradd
  # on PATH (users are declarative), so pre-create the user here. Wings
  # detects it exists and skips its own creation step.
  users.users.pelican = {
    isSystemUser = true;
    group = "pelican";
    home = "/var/lib/pelican";
    description = "Pelican game-server runtime user";
  };
  users.groups.pelican = {};

  systemd.tmpfiles.rules = [
    "d /etc/pelican             0755 root root -"
    "d /var/lib/pelican         0700 root root -"
    "d /var/lib/pelican/volumes 0700 root root -"
    "d /var/lib/pelican/logs    0700 root root -"
  ];

  # nostromo's impermanence doesn't track /var/log; keep Wings's logs
  # under /var/lib/pelican/logs so they're covered by /var/lib persistence.
  environment.persistence."/persist".directories = [
    "/etc/pelican"
    "/var/lib/pelican"
  ];

  systemd.services.wings = {
    description = "Pelican Wings";
    after = [ "podman.service" "podman.socket" "network-online.target" ];
    wants = [ "podman.socket" "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      ExecStart = "${wings}/bin/wings --config /etc/pelican/config.yml";
      Restart = "on-failure";
      RestartSec = "5s";
      LimitNOFILE = "4096";
      User = "root";
      Group = "root";
      # Wings expects /var/run/docker.sock by default. dockerCompat on this
      # host exposes a Docker-API-compatible socket at /run/podman/podman.sock;
      # point Wings at it explicitly so it manages game containers via podman.
      Environment = "DOCKER_HOST=unix:///run/podman/podman.sock";
    };
    unitConfig = {
      StartLimitIntervalSec = "180s";
      StartLimitBurst = "30";
    };
  };

  # No firewall ports needed for Wings itself - tailscale0 is a trusted
  # interface (shared/tailscale.nix), so the panel on ishimura reaches Wings
  # over tailnet without explicit holes. Game-server-specific ports get
  # added per-game when each server is provisioned and needs public access
  # via Pangolin raw TCP/UDP resources.
}
