{ pkgs, ... }:

{
  services.desktopManager.plasma6.enable = true;

  programs.hyprland = {
    enable = true;
    xwayland.enable = true;
  };

  services.greetd.enable = true;

  programs.regreet.enable = true;

  xdg.portal = {
    enable = true;
    extraPortals = [ pkgs.xdg-desktop-portal-hyprland ];
  };

  security.polkit.enable = true;
}
