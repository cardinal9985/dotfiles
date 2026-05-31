{ pkgs, ... }:

{
  services = {
    desktopManager.plasma6.enable = true;
    greetd.enable = true;
  };

  programs = {
    hyprland = {
      enable = true;
      xwayland.enable = true;
    };
    regreet.enable = true;
  };

  xdg = {
    mime.defaultApplications = {
      "x-scheme-handler/http"  = "zen.desktop";
      "x-scheme-handler/https" = "zen.desktop";
      "text/html"              = "zen.desktop";
    };
    portal = {
      enable = true;
      extraPortals = [ pkgs.xdg-desktop-portal-hyprland ];
    };
  };
}
