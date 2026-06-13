{ ... }:

{

  imports = [
    ./locale.nix
    ./fonts.nix
    ./hardening.nix
    ./netavark-cleanup.nix
    ./services.nix
    ./nix-settings.nix
    ./tailscale.nix
  ];

}
