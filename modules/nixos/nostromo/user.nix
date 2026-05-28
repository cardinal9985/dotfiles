{ config, ... }:

{
  security.sudo.wheelNeedsPassword = true;

  users = {
    mutableUsers = false;
    users = {
      maxwell = {
        isNormalUser = true;
        extraGroups = [ "wheel" "networkmanager" "video" ];
        hashedPasswordFile = config.sops.secrets."users/maxwell_password".path;
      };
      root.hashedPassword = "!";
    };
  };
}
