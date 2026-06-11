{ ... }:

{
  users.users.maxwell.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM2KfU+Ni17d8jqgteD4Xr/i19LrAjFFiD9QpqS4qhz3"
  ];

  services = {
    openssh = {
      enable = true;
      ports = [ 36475 ];
      settings = {
        PasswordAuthentication = false;
        KbdInteractiveAuthentication = false;
        PermitRootLogin = "no";
        AllowUsers = [ "maxwell" ];
      };
    };

    fail2ban = {
      enable = true;
      maxretry = 5;
      bantime = "24h";
      bantime-increment = {
        enable = true;
        formula = "ban.Time * math.exp(float(ban.Count+1)*banFactor)/math.exp(1*banFactor)";
        maxtime = "168h";
        overalljails = true;
      };
      ignoreIP = [
        "10.0.0.0/8" "172.16.0.0/12" "192.168.0.0/16"
        "100.64.0.0/10"
      ];
      jails.sshd.settings.port = "36475";
    };
  };
}
