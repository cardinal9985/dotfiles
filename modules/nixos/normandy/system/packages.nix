{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    git
    curl
    wget
    htop
    btop
    iotop
    iftop
    nethogs
    ncdu
    jq
    mtr
    tcpdump
    unzip
    lsof
    smartmontools
  ];
}
