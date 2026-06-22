{ ... }:

{
  systemd.tmpfiles.rules = [
    "d /persist/privatebin      0750 root root -"
    "d /persist/privatebin/data 0755 65534 65534 -"
  ];

  virtualisation.oci-containers.containers.privatebin = {
    image   = "docker.io/privatebin/nginx-fpm-alpine:latest";
    volumes = [ "/persist/privatebin/data:/srv/data" ];
    ports   = [ "127.0.0.1:4549:8080" ];
  };
}
