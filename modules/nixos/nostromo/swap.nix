{ pkgs, ... }:

{

  # Swapfile creation safety net:
  # BTRFS swapfiles require Copy-on-Write to be disabled on the subvolume
  # (via chattr +C) before the file is created, the kernel will refuse to
  # use a swapfile that has CoW enabled. Disko does not handle this
  # automatically when it creates the @swap subvolume, so if the disk is
  # ever reformatted with disko the swapfile would be missing. This service
  # runs at boot and recreates it correctly if it doesn't exist.
  systemd.services.create-swapfile = {
    description = "Create btrfs swapfile";
    requiredBy = [ "swap.target" ];
    before = [ "swap.target" ];
    unitConfig.DefaultDependencies = "no";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      if [ ! -f /swap/swapfile ]; then
        # Must disable CoW on the directory before creating the file —
        # chattr +C cannot be applied retroactively to existing files.
        ${pkgs.e2fsprogs}/bin/chattr +C /swap
        ${pkgs.btrfs-progs}/bin/btrfs filesystem mkswapfile --size 8G /swap/swapfile
      fi
    '';
  };

}
