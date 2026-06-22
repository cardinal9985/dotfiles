{ config, lib, pkgs, ... }:

let
  elementWebSrc = pkgs.element-web.override {
    conf = {
      default_server_config."m.homeserver" = {
        base_url = "https://chat.ishimura.lol";
        server_name = "ishimura.lol";
      };
      brand = "USG Ishimura";
      default_theme = "dark";
      disable_guests = true;
      room_directory.servers = [ "ishimura.lol" ];
    };
  };
  elementWeb = pkgs.runCommand "element-web-self-contained" { } ''
    mkdir -p $out
    cp -rL ${elementWebSrc}/. $out/
  '';
in
{
  sops.secrets."tuwunel/oidc_client_secret" = {
    owner = "tuwunel";
    mode  = "0400";
  };

  services.matrix-tuwunel = {
    enable = true;
    settings.global = {
      server_name        = "ishimura.lol";
      address            = [ "127.0.0.1" ];
      port               = [ 6167 ];
      allow_registration = false;
      allow_federation   = false;
      allow_encryption   = true;
      identity_provider = [
        {
          brand              = "VoidAuth";
          name               = "VoidAuth";
          client_id          = "tuwunel";
          client_secret_file = config.sops.secrets."tuwunel/oidc_client_secret".path;
          issuer_url         = "https://auth.ishimura.lol";
          callback_url       = "https://chat.ishimura.lol/_matrix/client/unstable/login/sso/callback/tuwunel";
          trusted            = true;
          registration       = true;
          userid_claims      = [ "preferred_username" ];
        }
      ];
    };
  };

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/tuwunel"; user = "tuwunel"; group = "tuwunel"; mode = "0700"; }
  ];

  systemd.tmpfiles.rules = [
    "d /persist/var/lib/tuwunel 0700 tuwunel tuwunel - -"
  ];

  systemd.services.tuwunel.serviceConfig = {
    DynamicUser  = lib.mkForce false;
    PrivateUsers = lib.mkForce false;
  };

  virtualisation.oci-containers.containers.element-web = {
    image   = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
    cmd     = [ "httpd" "-f" "-p" "80" "-h" "/www" ];
    volumes = [ "${elementWeb}:/www:ro" ];
    ports   = [ "127.0.0.1:4548:80" ];
  };

  system.activationScripts.matrix-well-known = ''
    mkdir -p /persist/pangolin/errors/.well-known/matrix
    printf '{"m.server":"chat.ishimura.lol:443"}' \
      > /persist/pangolin/errors/.well-known/matrix/server
    printf '{"m.homeserver":{"base_url":"https://chat.ishimura.lol"}}' \
      > /persist/pangolin/errors/.well-known/matrix/client
  '';
}
