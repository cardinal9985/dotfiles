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
        extraGroups = [ "wheel" ];
        hashedPassword = "$6$Cztsfx0LpCPi9EoI$N1jHLZtVyi3uYo4.QT6MAeSvz2Vngzbv7qDVBSIj30vH7XQYcKKCzf4kCyPPMRqjNaNI2Id8JN76yTJnYv7wO1";
      };
      root.hashedPassword = "!";
    };
  };
}
