{ config, pkgs, ... }:

{
  programs.zsh.enable = true;

  users = {
    mutableUsers = false;
    users = {
      maxwell = {
        isNormalUser = true;
        shell = pkgs.zsh;
        extraGroups = [ "wheel" "networkmanager" "video" "audio" ];
        hashedPasswordFile = config.sops.secrets."users/maxwell_password".path;
      };
      root.hashedPassword = "!";
    };
  };
}


