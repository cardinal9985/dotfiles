{ pkgs, ... }:

{
  # Slim VPS toolset: just what's useful for debugging when something breaks
  # at 3am. Keep this minimal; bloat costs disk + closure size during deploys.
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
