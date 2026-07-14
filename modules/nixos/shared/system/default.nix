{ ... }:

{
  imports = [
    ./bridge-user.nix
    ./fonts.nix
    ./hardening.nix
    ./locale.nix
    ./nix-settings.nix
    ./ntfy-on-failure.nix
    ./services.nix
  ];
}
