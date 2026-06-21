{ ... }:

{
  systemd.tmpfiles.rules = [
    "d /persist/synctube      0750 root root -"
    "d /persist/synctube/user 0750 root root -"
  ];

  virtualisation.oci-containers.containers.watch2gether = {
    image   = "docker.io/neneya/synctube:latest";
    volumes = [ "/persist/synctube/user:/usr/src/app/user" ];
    ports   = [ "127.0.0.1:4545:4200" ];
  };
}
