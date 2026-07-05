{ pkgs, inputs, ... }:

{
  environment.systemPackages = [
    inputs.nix-gaming.packages.${pkgs.system}.mo2installer
    pkgs.protontricks
    pkgs.winetricks
  ];
}
