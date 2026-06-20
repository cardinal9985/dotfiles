{ pkgs, ... }:

{
  boot.supportedFilesystems = [ "nfs" ];
  boot.kernelModules = [ "nfsv4" ];
  nix-mineral.settings.etc.kicksecure-module-blacklist = false;
  fileSystems."/mnt/storage" = {
    device = "100.92.76.121:/";
    fsType = "nfs4";
    options = [
      "x-systemd.automount"
      "noauto"
      "_netdev"
      "soft"
      "timeo=30"
      "retrans=2"
      "nofail"
    ];
  };
}
