{ ... }:

{
  users.users.maxwell.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM2KfU+Ni17d8jqgteD4Xr/i19LrAjFFiD9QpqS4qhz3"
  ];

  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = "no";
      AllowUsers = [ "maxwell" ];
    };
  };
}
