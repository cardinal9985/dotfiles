{ config, pkgs, ... }:

{
  system.activationScripts.cleanup-hm-backups.text = ''
    find /home/maxwell -maxdepth 4 -name "*.backup" -delete 2>/dev/null || true
  '';

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


