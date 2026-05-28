{ pkgs, ... }:

{

environment.systemPackages = with pkgs; [
  git
  curl
  wget
  nano
  parted
  pciutils
  usbutils
  age
  sops
  nvtopPackages.nvidia
  smartmontools
];

}
