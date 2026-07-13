{ pkgs, ... }:

{
  home.packages = with pkgs; [
    godot-mono      # Game Engine
    blender         # 3D Modeling
    material-maker  # Procedural Materials Authoring
    libresprite     # Sprite Editor
    pixelorama      # Pixel Art
  ];
}
