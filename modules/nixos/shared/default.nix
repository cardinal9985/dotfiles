{ ... }:

{

  imports = [
    ./locale.nix
    ./fonts.nix
    ./hardening.nix
    ./netavark-cleanup.nix
    ./ntfy-on-failure.nix
    ./services.nix
    ./nix-settings.nix
    ./tailscale.nix
  ];

}
