{ pkgs, ... }:

{
  home.packages = with pkgs; [
    grimblast        # Screenshot Tool
    grim             # Screenshot Backend
    slurp            # Region Selection
    swappy           # Screenshot Annotation
    cliphist         # Clipboard History
    wl-clipboard     # Wayland Clipboard
    playerctl        # Media Key Control
    pavucontrol      # Volume Mixer
    hyprpolkitagent  # Authentication Agent
  ];
}
