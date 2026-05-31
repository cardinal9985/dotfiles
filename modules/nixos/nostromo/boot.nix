{ pkgs, ... }:

{
  boot = {
    kernelParams = [
      "iommu=pt"
      "amd_iommu=on" # AMD Page Fault Fix
      "quiet"
      "splash"
      "rd.plymouth=1"
      "video=DP-6:2560x1080@200"
      "plymouth.use-simpledrm=1"
    ];

    kernelPackages = pkgs.linuxPackages_zen;

    kernelModules = [ "kvm-amd" ];

    tmp.cleanOnBoot = true;

    plymouth.enable = true;

    supportedFilesystems = [ "ntfs" ];

    loader = {
      efi.canTouchEfiVariables = true;
      systemd-boot = {
        enable = true;
        configurationLimit = 20;
      };
    };

    initrd = {
      supportedFilesystems = [ "btrfs" ];
      systemd = {
        enable = true;
        # Allow root access in initrd emergency shell for debugging
        # Safe to leave enabled — only accessible if boot fails
        emergencyAccess = true;
        services.rollback = {
          description = "Rollback BTRFS root subvolume to blank snapshot";
          wantedBy = [ "initrd.target" ];
          after = [ "systemd-cryptsetup@cryptroot.service" ];
          requires = [ "systemd-cryptsetup@cryptroot.service" ];
          before = [ "sysroot.mount" ];
          unitConfig.DefaultDependencies = "no";
          serviceConfig.Type = "oneshot";
          script = ''
            set -x

            mkdir -p /btrfs_tmp
            mount /dev/mapper/cryptroot /btrfs_tmp

            if [[ -e /btrfs_tmp/@ ]]; then
              mkdir -p /btrfs_tmp/old_roots
              timestamp=$(date --date="@$(stat -c %Y /btrfs_tmp/@)" "+%Y-%m-%d_%H-%M-%S")
              echo "Moving @ to old_roots/$timestamp"
              mv /btrfs_tmp/@ "/btrfs_tmp/old_roots/$timestamp"
            fi

            shopt -s nullglob
            for snapshot in /btrfs_tmp/old_roots/*/; do
              echo "Deleting old root: $snapshot"
              btrfs subvolume delete "$snapshot" || echo "WARNING: failed to delete $snapshot"
            done
            shopt -u nullglob

            echo "Creating @ from @blank"
            btrfs subvolume snapshot /btrfs_tmp/@snapshots/@blank /btrfs_tmp/@
            umount /btrfs_tmp
          '';
        };
      };
    };
  };
}
