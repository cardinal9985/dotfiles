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
  # into /etc/modprobe.d/nm-module-blacklist.conf, which makes any attempt to
  # load nfs/nfsv4 fail with "Invalid argument". Override with a higher-priority
  # modprobe config (zz- sorts last) that bypasses the install directive only
  # for the NFS modules. Rest of the kicksecure blacklist (dccp, cramfs, etc.)
  # stays intact.
  environment.etc."modprobe.d/zz-allow-nfs.conf".text = ''
    install nfs ${pkgs.kmod}/bin/modprobe --ignore-install nfs $CMDLINE_OPTS
    install nfsv2 ${pkgs.kmod}/bin/modprobe --ignore-install nfsv2 $CMDLINE_OPTS
    install nfsv3 ${pkgs.kmod}/bin/modprobe --ignore-install nfsv3 $CMDLINE_OPTS
    install nfsv4 ${pkgs.kmod}/bin/modprobe --ignore-install nfsv4 $CMDLINE_OPTS
    install nfs_acl ${pkgs.kmod}/bin/modprobe --ignore-install nfs_acl $CMDLINE_OPTS
    install nfs_layout_nfsv41_files ${pkgs.kmod}/bin/modprobe --ignore-install nfs_layout_nfsv41_files $CMDLINE_OPTS
    install nfs_layout_flexfiles ${pkgs.kmod}/bin/modprobe --ignore-install nfs_layout_flexfiles $CMDLINE_OPTS
  '';

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
