{ pkgs, inputs, ... }:

{
  home.packages = [
    # Built from cardinal9985/loadout via its own flake. Ships the binary
    # wrapped with runtime PATH (p7zip, unar, git) + LD_LIBRARY_PATH (GUI
    # libs), plus the .desktop entry and hicolor icons so it shows up in
    # Wofi / rofi / any XDG-aware launcher.
    inputs.loadout.packages.${pkgs.system}.default
  ];
}
