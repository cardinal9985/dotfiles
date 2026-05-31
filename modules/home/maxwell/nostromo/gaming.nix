{ pkgs, inputs, ... }:

{
  home.packages = with pkgs; [
    mangohud
    lutris
    heroic
    steamcmd
    vintagestory
    rimsort
    ckan
    doomrunner
    uzdoom
    inputs.nix-citizen.packages.${pkgs.stdenv.hostPlatform.system}.rsi-launcher

    (inputs.prismlauncher-cracked.packages.${pkgs.stdenv.hostPlatform.system}.prismlauncher.override {
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
