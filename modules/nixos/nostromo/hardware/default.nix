{ ... }:
{
  imports = [
    ./boot.nix
    ./gpu.nix
    ./audio.nix
    ./bluetooth.nix
    ./peripherals.nix
    ./power.nix
    ./swap.nix
  ];
}
