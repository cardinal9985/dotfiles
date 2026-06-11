{ config, pkgs, ... }:

{
  security.sudo.wheelNeedsPassword = false;

  programs.zsh.enable = true;

  users = {
    mutableUsers = false;
    users = {
      maxwell = {
        isNormalUser = true;
        shell = pkgs.zsh;
        extraGroups = [ "wheel" "media" ];
        hashedPasswordFile = config.sops.secrets."users/maxwell_password".path;
      };
      root.hashedPassword = "!";
    };
  };
}
