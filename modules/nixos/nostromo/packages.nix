{ pkgs, ... }:

{

environment.systemPackages = with pkgs; [
  git
  curl
  wget
  nano
  parted
  pciutils
  nh
  usbutils
  age
  sops
  nvtopPackages.nvidia
  smartmontools
];

}
