{ pkgs, ... }:

{
  security.sudo.wheelNeedsPassword = true;

  programs.zsh.enable = true;

  users = {
    mutableUsers = false;
    users = {
      maxwell = {
        isNormalUser = true;
        shell = pkgs.zsh;
        extraGroups = [ "wheel" ];
        hashedPassword = "$y$j9T$e9TjU96OOhsozygzUn2Ek.$B3Ge9v2acnGgsNGPofEtMIt14V/dHmhNR/0fUr.ArN3";
      };
      root.hashedPassword = "!";
    };
  };
}
