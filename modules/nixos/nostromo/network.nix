{ ... }:

{
  networking = {
    hostName = "nostromo";
    networkmanager.enable = true;
    firewall = {
      enable = true;
      allowedTCPPorts = [ 36475 43122 ]; # 36475 = SSH 43122 = Nicotine
    };
  };

  services.resolved = {
    enable = true;
    settings.Resolve = {
      # NOTE: Disabled, allow-downgrade was causing DNSSEC validation failures for
      # legitimate domains (Spotify CDN, Steam, Discord) that don't sign their
      # records. Quad9 (9.9.9.9) handles DNSSEC validation upstream so I get
      # the security benefit without resolved breaking resolution.
      DNSSEC = "false";
      Domains = [ "~." ];
      FallbackDNS = [ "9.9.9.9" "149.112.112.112" ];
    };
  };
}
