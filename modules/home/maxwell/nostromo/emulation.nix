# modules/home/maxwell/nostromo/emulation.nix
{ pkgs, ... }:

{
  home.packages = with pkgs; [
    pegasus-frontend
    pcsx2
    rpcs3
    shadps4
    xenia-canary
    ryubing
    xemu
    antimicrox

    (retroarch.withCores (cores: with cores; [
      snes9x
    ]))
  ];

  # Pico-8 is commercial, binary lives at /persist/apps/pico8/pico8
  # Download from https://www.lexaloffle.com/pico-8.php and place there
  home.sessionVariables = {
    PATH = "$PATH:/persist/apps/pico8";
  };

  # gameOS theme for Pegasus
  xdg.configFile."pegasus-frontend/themes/gameOS" = {
    source = pkgs.fetchFromGitHub {
      owner = "PlayingKarrde";
      repo = "gameOS";
      rev = "master";
      sha256 = "sha256-1mwrk8dk6rbr72nr32bnn524agjq01x1fyih1yxm7m5h8rxlh6hh=";
    };
  };

  xdg.configFile."pegasus-frontend/config/game_dirs.txt".text = ''
    /run/media/maxwell/X8/games/roms/arcade
    /run/media/maxwell/X8/games/roms/atari2600
    /run/media/maxwell/X8/games/roms/atari5200
    /run/media/maxwell/X8/games/roms/atari7800
    /run/media/maxwell/X8/games/roms/atarilynx
    /run/media/maxwell/X8/games/roms/colecovision
    /run/media/maxwell/X8/games/roms/cps1
    /run/media/maxwell/X8/games/roms/cps2
    /run/media/maxwell/X8/games/roms/cps3
    /run/media/maxwell/X8/games/roms/dos
    /run/media/maxwell/X8/games/roms/gb
    /run/media/maxwell/X8/games/roms/gba
    /run/media/maxwell/X8/games/roms/gbc
    /run/media/maxwell/X8/games/roms/gamegear
    /run/media/maxwell/X8/games/roms/mastersystem
    /run/media/maxwell/X8/games/roms/megadrive
    /run/media/maxwell/X8/games/roms/msx
    /run/media/maxwell/X8/games/roms/n64
    /run/media/maxwell/X8/games/roms/neogeo
    /run/media/maxwell/X8/games/roms/neogeocd
    /run/media/maxwell/X8/games/roms/nes
    /run/media/maxwell/X8/games/roms/ngpc
    /run/media/maxwell/X8/games/roms/odyssey2
    /run/media/maxwell/X8/games/roms/pcengine
    /run/media/maxwell/X8/games/roms/pcenginecd
    /run/media/maxwell/X8/games/roms/ps2
    /run/media/maxwell/X8/games/roms/psx
    /run/media/maxwell/X8/games/roms/sega32x
    /run/media/maxwell/X8/games/roms/segacd
    /run/media/maxwell/X8/games/roms/sg-1000
    /run/media/maxwell/X8/games/roms/snes
    /run/media/maxwell/X8/games/roms/tic80
    /run/media/maxwell/X8/games/roms/vectrex
    /run/media/maxwell/X8/games/roms/virtualboy
    /run/media/maxwell/X8/games/roms/wonderswancolor
    /run/media/maxwell/X8/games/roms/zxspectrum
    /run/media/maxwell/X8/games/roms/pico8
  '';

  xdg.configFile."pegasus-frontend/config/settings.txt".text = ''
    general.fullscreen: false
    general.input-mouse-support: true
    general.theme: gameOS
  '';

  # Pico-8 metadata for Pegasus
  xdg.configFile."pegasus-frontend/config/metadata.pegasus.txt".text = ''
    collection: Pico-8
    shortname: pico8
    launch: /persist/apps/pico8/pico8 "{file.path}"
    extension: p8, p8.png

    files: /run/media/maxwell/X8/games/roms/pico8
  '';
}
