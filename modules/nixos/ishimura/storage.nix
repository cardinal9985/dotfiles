{ pkgs, ... }:

{
  fileSystems."/mnt/disk1" = {
    device = "/dev/disk/by-uuid/72fc1309-08b0-4688-8271-d3bbe9757e21";
    fsType = "ext4";
    options = [ "defaults" "nofail" ];
  };

  fileSystems."/mnt/disk2" = {
    device = "/dev/disk/by-uuid/46103d7b-228d-415f-b097-1d21b2a3dd9f";
    fsType = "ext4";
    options = [ "defaults" "nofail" ];
  };

  fileSystems."/mnt/storage" = {
    device = "/mnt/disk1:/mnt/disk2";
    fsType = "fuse.mergerfs";
    options = [
      "defaults"
      "allow_other"
      "use_ino"
      "cache.files=partial"
      "dropcacheonclose=true"
      "category.create=mfs"
      "nofail"
    ];
    depends = [ "/mnt/disk1" "/mnt/disk2" ];
  };

  environment.systemPackages = [ pkgs.mergerfs ];

  services.btrfs.autoScrub = {
    enable = true;
    interval = "monthly";
  };
}
