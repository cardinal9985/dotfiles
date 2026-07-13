{ lib, ... }:

{
  services.unbound = {
    enable = true;
    resolveLocalQueries = false;
    settings = {
      server = {
        interface = [ "127.0.0.1" ];
        port = 5335;
        access-control = [
          "127.0.0.0/8 allow"
        ];
        hide-identity = true;
        hide-version = true;
        harden-glue = true;
        harden-dnssec-stripped = true;
        use-caps-for-id = true;
        qname-minimisation = true;
        aggressive-nsec = true;
        prefetch = true;
        prefetch-key = true;
        cache-min-ttl = 300;
        cache-max-ttl = 86400;
      };
    };
  };

  services.adguardhome = {
    enable = true;
    mutableSettings = true;
    host = "0.0.0.0";
    port = 3000;
    openFirewall = true;
  };

  users.users.adguardhome = {
    isSystemUser = true;
    group = "adguardhome";
    home = "/var/lib/AdGuardHome";
  };

  users.groups.adguardhome = { };
  systemd.services.adguardhome.serviceConfig = {
    DynamicUser = lib.mkForce false;
    User = "adguardhome";
    Group = "adguardhome";
  };

  networking.firewall.allowedTCPPorts = [ 53 3000 ];
  networking.firewall.allowedUDPPorts = [ 53 ];

  services.resolved.enable = lib.mkForce false;

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/AdGuardHome"; user = "adguardhome"; group = "adguardhome"; mode = "0700"; }
    "/var/lib/unbound"
  ];
}
