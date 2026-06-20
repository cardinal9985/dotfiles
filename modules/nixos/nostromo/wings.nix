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
    "d /etc/pelican             0755 root root -"
    "d /var/lib/pelican         0700 root root -"
    "d /var/lib/pelican/volumes 0700 root root -"
    "d /var/lib/pelican/logs    0700 root root -"
  ];

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
      Environment = "DOCKER_HOST=unix:///run/podman/podman.sock";
    };
    unitConfig = {
      StartLimitIntervalSec = "180s";
      StartLimitBurst = "30";
    };
  };
}
