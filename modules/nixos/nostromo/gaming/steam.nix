{ pkgs, ... }:

{
  programs.steam = {
    enable = true;
    gamescopeSession.enable = true;
    remotePlay.openFirewall = false;
    dedicatedServer.openFirewall = false;
    localNetworkGameTransfers.openFirewall = false;
    package = pkgs.steam.override {
      extraPkgs = (pkgs: with pkgs; [
        gamemode
        mangohud
        xdg-user-dirs
      ]);
      extraProfile = ''
        export LD_PRELOAD="${pkgs.gamemode}/lib/libgamemodeauto.so"
      '';
    };
    extraCompatPackages = with pkgs; [
      proton-ge-bin
    ];
  };

  environment.sessionVariables = {
    STEAM_EXTRA_COMPAT_TOOLS_PATHS = "\${HOME}/.steam/root/compatibilitytools.d";
    __GL_SHADER_DISK_CACHE = "1";
    __GL_SHADER_DISK_CACHE_SKIP_CLEANUP = "1";
  };
}
