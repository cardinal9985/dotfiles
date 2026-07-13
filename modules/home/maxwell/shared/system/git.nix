# modules/home/maxwell/shared/git.nix
{ ... }:

{
  programs.git = {
    enable = true;

    signing = {
      key = "/home/maxwell/.ssh/id_ed25519";
      signByDefault = true;
    };

    settings = {
      user.name = "Maxwell";
      user.email = "252437093+cardinal9985@users.noreply.github.com";
      init.defaultBranch = "main";
      push.autoSetupRemote = true;
      gpg.format = "ssh";
      "gpg \"ssh\"".allowedSignersFile = "/home/maxwell/.ssh/allowed_signers";
      "url \"git@github.com:\"".insteadOf = "https://github.com/";
    };
  };

  home.file.".ssh/allowed_signers".text = ''
    252437093+cardinal9985@users.noreply.github.com namespaces="git" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDDrz3C9ShHHUllPlEfAdS8wPoQkBLvCp07CVPmXOOUc
  '';
}
