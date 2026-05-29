{ pkgs, ... }:

{
  home.packages = with pkgs; [
    easyeffects
  ];

  services.easyeffects = {
    enable = true;
    preset = "music";
  };

  xdg.dataFile."easyeffects/output/music.json".source  = ../../../../config/easyeffects/music.json;
  xdg.dataFile."easyeffects/output/gaming.json".source = ../../../../config/easyeffects/gaming.json;
  xdg.dataFile."easyeffects/output/movies.json".source = ../../../../config/easyeffects/movies.json;
  xdg.dataFile."easyeffects/output/flat.json".source   = ../../../../config/easyeffects/flat.json;
  xdg.dataFile."easyeffects/output/night.json".source  = ../../../../config/easyeffects/night.json;
  xdg.dataFile."easyeffects/output/voice.json".source  = ../../../../config/easyeffects/voice.json;
}
