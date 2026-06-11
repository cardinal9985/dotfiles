{ ... }:

{

  imports = [
    ./locale.nix
    ./fonts.nix
    ./hardening.nix
    ./services.nix
    ./nix-settings.nix
    ./tailscale.nix
  ];

}
