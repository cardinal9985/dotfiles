{ ... }:

{
  disko.devices = {
    disk = {
      main = {
        type = "disk";
        device = "/dev/disk/by-id/nvme-CT2000T500SSD8_25064DFD15CA";
        content = {
          type = "gpt";
          partitions = {
            ESP = {
              size = "1024M";
              type = "EF00";
              content = {
                type = "filesystem";
                format = "vfat";
                mountpoint = "/boot";
                mountOptions = [ "fmask=0022" "dmask=0022" ];
              };
            };
            primary = {
              size = "100%";
              content = {
                type = "luks";
                name = "cryptroot";
                settings = {
                  allowDiscards = true;
                };
                content = {
                  type = "btrfs";
                  extraArgs = [ "-L" "nixos" ];
                  subvolumes = {
                    "@" = {
                      mountpoint = "/";
                      mountOptions = [ "noatime" "compress=zstd:1" "ssd" "space_cache=v2" "discard=async" ];
                    };
                    "@nix" = {
                      mountpoint = "/nix";
                      mountOptions = [ "noatime" "compress=zstd:1" "ssd" "space_cache=v2" "discard=async" ];
                    };
                    "@persist" = {
                      mountpoint = "/persist";
                      mountOptions = [ "noatime" "compress=zstd:1" "ssd" "space_cache=v2" "discard=async" ];
                    };
                    "@home" = {
                      mountpoint = "/home";
                      mountOptions = [ "noatime" "compress=zstd:1" "ssd" "space_cache=v2" "discard=async" ];
                    };
                    "@log" = {
                      mountpoint = "/var/log";
                      mountOptions = [ "noatime" "compress=zstd:1" "ssd" "space_cache=v2" "discard=async" ];
                    };
                    "@snapshots" = {
                      mountpoint = "/.snapshots";
                      mountOptions = [ "noatime" "compress=zstd:1" "ssd" "space_cache=v2" "discard=async" ];
                    };
                    "@swap" = {
                      mountpoint = "/swap";
                      mountOptions = [ "noatime" ];
                    };
                  };
                };
              };
            };
          };
        };
      };
    };
  };
}
