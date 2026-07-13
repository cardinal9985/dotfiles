{ ... }:

{
  systemd.tmpfiles.rules = [
    "d /mnt/storage/mods                0755 maxwell users -"
    "d /mnt/storage/mods/tarkov         0755 maxwell users -"
    "d /mnt/storage/mods/vintage-story  0755 maxwell users -"
  ];

  virtualisation.oci-containers.containers.mods-server = {
    image = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
    cmd = [ "httpd" "-f" "-p" "8087" "-h" "/www" ];
    volumes = [ "/mnt/storage/mods:/www:ro" ];
    extraOptions = [ "--network=host" ];
  };

  systemd.services.podman-mods-server = {
    after = [ "mnt-storage.mount" ];
    requires = [ "mnt-storage.mount" ];
  };
}
