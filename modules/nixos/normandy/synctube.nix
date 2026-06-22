{ pkgs, ... }:

let
  dailyCleanScript = pkgs.writeShellScript "synctube-daily-clean" ''
    ${pkgs.systemd}/bin/systemctl stop podman-synctube.service || true
    rm -rf /persist/synctube/user/res/cache/* || true
    if [ -f /persist/synctube/user/state.json ]; then
      ${pkgs.jq}/bin/jq '.messages = [] | .videoList = [] | .itemPos = 0' \
        /persist/synctube/user/state.json > /persist/synctube/user/state.json.tmp \
        && mv /persist/synctube/user/state.json.tmp /persist/synctube/user/state.json
    fi
    ${pkgs.systemd}/bin/systemctl start podman-synctube.service
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/synctube      0750 root root -"
    "d /persist/synctube/user 0750 root root -"
  ];

  virtualisation.oci-containers.containers.synctube = {
    image   = "docker.io/neneya/synctube:latest";
    volumes = [ "/persist/synctube/user:/usr/src/app/user" ];
    ports   = [ "127.0.0.1:4545:4200" ];
  };

  systemd.services.synctube-daily-clean = {
    description = "Clear SyncTube video cache, chat history, and playlist";
    serviceConfig = {
      Type      = "oneshot";
      ExecStart = "${dailyCleanScript}";
    };
  };

  systemd.timers.synctube-daily-clean = {
    description = "Daily SyncTube cache + chat + playlist cleanup";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "daily";
      Persistent = true;
    };
  };
}
