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
    # Clients auth via time-bound HMAC-derived username:password derived from
    # this shared secret. No per-user accounts. RetroArch netplay, browser
    # EmulatorJS netplay, future Jitsi all use this pattern.
    use-auth-secret = true;
    static-auth-secret-file = config.sops.secrets."coturn/static_auth_secret".path;

    # Standard STUN/TURN port. TLS skipped for the initial deploy - WebRTC
    # media (the actual game traffic between peers) is DTLS-encrypted end-
    # to-end regardless of whether coturn itself runs TLS. Add TURNS later
    # by requesting a cert via security.acme + porkbun DNS-01.
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
