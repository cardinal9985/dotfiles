{ pkgs, inputs, ... }:

{
  home.packages = with pkgs; [
    mangohud
    heroic
    steamcmd
    vintagestory
    rimsort
    ckan
    doomrunner
    uzdoom
    inputs.nix-citizen.packages.${pkgs.stdenv.hostPlatform.system}.rsi-launcher

    (pkgs.prismlauncher.override {
      additionalPrograms = [
        ffmpeg
        zenity
      ];
      gamemodeSupport = true;
      jdks = [
        zulu8
        zulu17
        zulu21
      ];
    })
  ];
}
