{ pkgs, ... }:

{
  home.packages = with pkgs; [
    gpg-tui
    pinentry-qt
  ];

  services.gpg-agent = {
    enable = true;
    enableSshSupport = true;
    defaultCacheTtl = 86400;
    maxCacheTtl = 604800;
    defaultCacheTtlSsh = 86400;
    maxCacheTtlSsh = 604800;
    pinentry.package = pkgs.pinentry-qt;
  };

  programs.gpg = {
    enable = true;
    settings = {
      default-key = "CC2EF0A6AEC22390";
      use-agent = true;
    };
  };

  home.sessionVariables = {
    SSH_AUTH_SOCK = "$(gpgconf --list-dirs agent-ssh-socket)";
  };
}
