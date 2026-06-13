{ ... }:

{
  # Ensure the NFSv4 kernel module + userspace are present. Without this,
  # mounts fail with "No such device" because no driver claims `nfs4` fsType.
  boot.supportedFilesystems = [ "nfs" ];

  # NFS client mount of ishimura's /mnt/storage over the tailnet.
  # Encrypted by tailscale; NFSv4 simple auth is sufficient since the
  # ishimura export pins to nostromo's tailnet IP.
  fileSystems."/mnt/storage" = {
    device = "100.92.76.121:/";  # ishimura tailnet IP, NFSv4 pseudo-root
    fsType = "nfs4";
    options = [
      "x-systemd.automount"  # lazy mount on first access
      "noauto"                # don't mount at boot
      "_netdev"               # require network up first
      "soft"                  # don't hang processes if ishimura is offline
      "timeo=30"              # 3-second RPC timeout (deciseconds)
      "retrans=2"             # retry twice before giving up
      "nofail"                # don't block boot if mount fails
    ];
  };
}
