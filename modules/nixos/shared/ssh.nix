{ ... }:

{

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
        enable = true; # Enable increment of bantime after each violation
        formula = "ban.Time * math.exp(float(ban.Count+1)*banFactor)/math.exp(1*banFactor)";
        maxtime = "168h"; # Do not ban for more than 1 week
        overalljails = true; # Calculate the bantime based on all the violations
      };
      ignoreIP = [
        "10.0.0.0/8" "172.16.0.0/12" "192.168.0.0/16"
      ];
    };
  };

}
