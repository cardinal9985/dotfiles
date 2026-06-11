{ pkgs, ... }:

{

nixpkgs.config.permittedInsecurePackages = [
  "electron-39.8.10"
];

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
  smartmontools
  colmena
];

}
