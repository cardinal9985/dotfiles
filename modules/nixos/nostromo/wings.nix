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
  users.users.pelican = {
    isSystemUser = true;
    group = "pelican";
    home = "/var/lib/pelican";
    description = "Pelican game-server runtime user";
  };
  users.groups.pelican = {};

  systemd.tmpfiles.rules = [
    "d /etc/pelican             0755 root root    -"
    # Group-traversable so pelican-run services (e.g. kf2.service) can
    # read into volume subdirs. Root still owns; per-volume perms
    # inside are set by Wings.
    "d /var/lib/pelican         0750 root pelican -"
    "d /var/lib/pelican/volumes 0750 root pelican -"
    "d /var/lib/pelican/logs    0700 root root    -"
  ];

  environment.persistence."/persist".directories = [
    "/etc/pelican"
    "/var/lib/pelican"
  ];

  # Hangar discovery placeholders for games still running inside Pelican
  # containers. Hangar tracks their up/down state via process probes on
  # nostromo so the homepage indicator can already flip to Hangar as its
  # source of truth. These entries get replaced when each game migrates
  # to a native systemd unit under modules/nixos/nostromo/<game>.nix
  # (Stages 5-6 of the hangar spec).
  environment.etc."hangar/servers.d/vintage-story.json".text = builtins.toJSON {
    slug            = "vintage-story";
    homepage_slug   = "vintage-story";
    name            = "Vintage Story";
    game_type       = "vintagestory";
    connect_address = "games.ishimura.lol:42420";
    status_probe    = {
      type    = "process";
      pattern = "VintagestoryServer";
    };
  };
  environment.etc."hangar/servers.d/tarkov-spt.json".text = builtins.toJSON {
    slug            = "tarkov-spt";
    homepage_slug   = "escape-from-tarkov-fika";
    name            = "Escape from Tarkov: Fika";
    game_type       = "tarkov-spt";
    connect_address = "https://games.ishimura.lol:6969";
    status_probe    = {
      type = "http";
      url  = "http://127.0.0.1:6969/";
    };
  };

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
      Environment = "DOCKER_HOST=unix:///run/podman/podman.sock";
    };
    unitConfig = {
      StartLimitIntervalSec = "180s";
      StartLimitBurst = "30";
    };
  };
}
