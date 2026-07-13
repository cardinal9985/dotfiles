{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    git
    curl
    wget
    htop
    btop
    lsof
    nftables
    smartmontools
    unzip
    iotop
    iftop
    nethogs
    ncdu
    jq
    mtr
    mediainfo
    sqlite
  ];
}
