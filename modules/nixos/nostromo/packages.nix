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
  jq
  bind.dnsutils
  parted
  pciutils
  nh
  usbutils
  age
  sops
  smartmontools
  colmena
  unzip
  iotop
  iftop
  ncdu
  nethogs
  mtr
];

}
