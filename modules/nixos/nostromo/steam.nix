{ pkgs, ... }:

{
  programs = {
    steam = {
      enable = true;
      gamescopeSession.enable = true;
      remotePlay.openFirewall = false;
      dedicatedServer.openFirewall = false;
      localNetworkGameTransfers.openFirewall = false;
      package = pkgs.steam.override {
        extraPkgs = (pkgs: with pkgs; [ gamemode ]);
        extraProfile = ''
          export LD_PRELOAD="${pkgs.gamemode}/lib/libgamemodeauto.so"
        '';
      };
      extraCompatPackages = with pkgs; [
        proton-ge-bin
      ];
    };
    gamescope.enable = true;
    gamemode.enable = true;

  };

  environment.systemPackages = with pkgs; [
    mangohud
  ];

  environment.sessionVariables = {
    STEAM_EXTRA_COMPAT_TOOLS_PATHS = "\${HOME}/.steam/root/compatibilitytools.d";
  };
}
