{ ... }:

# Tiny static file server that exposes /mnt/storage/mods/ on the tailnet.
# Pangolin routes ishimura.lol/mods/* through this. Public, no auth - any
# friend with the URL can grab a mod bundle.
#
# Read-only mount; uploads go through FileBrowser (filebrowser.nix) which
# has its own auth gate.

{
  systemd.tmpfiles.rules = [
    "d /mnt/storage/mods                0755 maxwell users -"
    "d /mnt/storage/mods/tarkov         0755 maxwell users -"
    "d /mnt/storage/mods/vintage-story  0755 maxwell users -"
  ];

  virtualisation.oci-containers.containers.mods-server = {
    image = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
    cmd = [ "httpd" "-f" "-p" "80" "-h" "/www" ];
    volumes = [ "/mnt/storage/mods:/www:ro" ];
    ports = [ "100.92.76.121:8087:80" ];
  };

  systemd.services.podman-mods-server = {
    after = [ "mnt-storage.automount" ];
    requires = [ "mnt-storage.automount" ];
  };
}
