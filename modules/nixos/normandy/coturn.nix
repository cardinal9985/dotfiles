{ config, ... }:

{
  sops.secrets."coturn/static_auth_secret" = {
    owner = "turnserver";
    group = "turnserver";
    mode = "0400";
  };

  services.coturn = {
    enable = true;
    realm = "turn.ishimura.lol";
    use-auth-secret = true;
    static-auth-secret-file = config.sops.secrets."coturn/static_auth_secret".path;
    listening-port = 3478;
    min-port = 49152;
    max-port = 50000;

    no-cli = true;
    extraConfig = ''
      no-loopback-peers
      no-multicast-peers
      no-stdout-log
      simple-log
    '';
  };

  networking.firewall = {
    allowedTCPPorts = [ 3478 ];
    allowedUDPPorts = [ 3478 ];
    allowedUDPPortRanges = [
      { from = 49152; to = 50000; }
    ];
  };
}
