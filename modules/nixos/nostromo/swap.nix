{ pkgs, ... }:

{
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
        # Must disable CoW on the directory before creating the file:
        # chattr +C cannot be applied retroactively to existing files.
        ${pkgs.e2fsprogs}/bin/chattr +C /swap
        ${pkgs.btrfs-progs}/bin/btrfs filesystem mkswapfile --size 8G /swap/swapfile
      fi
    '';
  };
}
