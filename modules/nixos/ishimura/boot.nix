{ ... }:

{
  boot = {
    initrd = {
      supportedFilesystems = [ "btrfs" ];
      systemd = {
        enable = true;
        services.rollback = {
          description = "Rollback BTRFS root subvolume to blank snapshot";
          wantedBy = [ "initrd.target" ];
          before = [ "sysroot.mount" ];
          unitConfig.DefaultDependencies = "no";
          serviceConfig.Type = "oneshot";
          script = ''
            set -x

            mkdir -p /btrfs_tmp
            mount -t btrfs -o subvol=/ /dev/disk/by-id/nvme-SAMCO_RX1_1TB_SSD_08092223A0122-part2 /btrfs_tmp

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
            btrfs subvolume snapshot /btrfs_tmp/@blank /btrfs_tmp/@
            umount /btrfs_tmp
          '';
        };
      };
    };

    loader = {
      efi.canTouchEfiVariables = true;
      systemd-boot = {
        enable = true;
        configurationLimit = 20;
      };
    };
  };
}
