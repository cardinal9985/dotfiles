{ pkgs, ... }:

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

  systemd.services.synctube-cache-clean = {
    description = "Clear SyncTube local video upload cache";
    serviceConfig = {
      Type = "oneshot";
      ExecStart = "${pkgs.bash}/bin/bash -c 'rm -rf /persist/synctube/user/res/cache/*'";
    };
  };

  systemd.timers.synctube-cache-clean = {
    description = "Daily SyncTube cache cleanup";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "daily";
      Persistent = true;
    };
  };
}
