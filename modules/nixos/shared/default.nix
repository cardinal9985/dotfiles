{ ... }:

{

  imports = [
    ./locale.nix
    ./fonts.nix
    ./hardening.nix
    ./netavark-cleanup.nix
    ./alloy.nix
    ./node-exporter.nix
    ./ntfy-on-failure.nix
    ./podman.nix
    ./services.nix
    ./nix-settings.nix
    ./tailscale.nix
  ];

}
