{ pkgs, ... }:

{
  # Ensure the NFSv4 kernel module + userspace are present. Without this,
  # mounts fail with "No such device" because no driver claims `nfs4` fsType.
  # `supportedFilesystems` adds initrd support; `kernelModules` makes it load
  # on every boot of the running system (needed for late-binding fileSystems
  # entries like /mnt/storage that aren't mounted at boot).
  boot.supportedFilesystems = [ "nfs" ];
  boot.kernelModules = [ "nfsv4" ];

  # nix-mineral's kicksecure-module-blacklist drops `install nfs* /bin/false`
  # into /etc/modprobe.d/nm-module-blacklist.conf, which makes loading nfs/nfsv4
  # fail with "Invalid argument". A zz- prefixed override file does NOT help:
  # modprobe processes install directives in file-load order and uses the FIRST
  # match (not the last). Disabling the whole blacklist is the only practical
  # fix; the modules it protects (dccp, cramfs, jffs2, etc.) aren't used on this
  # workstation.
  nix-mineral.settings.etc.kicksecure-module-blacklist = false;

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
