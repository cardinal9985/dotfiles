{ lib, ... }:

let
  critical = [
    "podman-pangolin"
    "podman-traefik"
    "podman-gerbil"
    "podman-voidauth"
    "podman-voidauth-db"
    "podman-ntfy"
    "podman-homepage"
    "podman-errorpages"
    "anubis-public"
    "crowdsec"
    "crowdsec-ntfy"
  ];
  alertFor = name: {
    "${name}".unitConfig.OnFailure = [ "ntfy-on-failure@%n.service" ];
  };
in
{
  systemd.services = lib.mkMerge (map alertFor critical);
}
