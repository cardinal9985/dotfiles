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
  ];
}
