{ lib, ... }:

{
  # Unbound: full recursive DNS resolver, talks to root + authoritative servers
  # directly. No third-party upstream sees the full query stream. AdGuard Home
  # forwards to this on 127.0.0.1:5335 for actual resolution.
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

  # AdGuard Home: ad blocking, query log, web UI. Forwards to Unbound for
  # recursive resolution. DNS on :53 for clients, web UI on :3000.
  services.adguardhome = {
    enable = true;
    mutableSettings = true;
    host = "0.0.0.0";
    port = 3000;
    openFirewall = true;
  };

  # Override AGH's DynamicUser=true so impermanence bind mounts work cleanly.
  # DynamicUser symlinks /var/lib/AdGuardHome to /var/lib/private/AdGuardHome
  # at runtime, which conflicts with the bind mount from /persist.
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

  # AGH's openFirewall only handles its web UI; DNS port 53 is not auto-opened.
  networking.firewall.allowedTCPPorts = [ 53 3000 ];
  networking.firewall.allowedUDPPorts = [ 53 ];

  # Disable systemd-resolved so it does not fight AGH for port 53.
  services.resolved.enable = lib.mkForce false;

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/AdGuardHome"; user = "adguardhome"; group = "adguardhome"; mode = "0700"; }
    "/var/lib/unbound"
  ];
}
