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
    # Host network avoids the default-bridge aardvark-dns collision with
    # AdGuard (AdGuard binds udp/53 on all interfaces incl. 10.88.0.1).
    # Firewall blocks 8087 from public; tailnet sees it via trusted iface.
    cmd = [ "httpd" "-f" "-p" "8087" "-h" "/www" ];
    volumes = [ "/mnt/storage/mods:/www:ro" ];
    extraOptions = [ "--network=host" ];
  };

  systemd.services.podman-mods-server = {
    after = [ "mnt-storage.mount" ];
    requires = [ "mnt-storage.mount" ];
  };
}
