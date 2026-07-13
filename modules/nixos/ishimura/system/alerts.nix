{ lib, ... }:

let
  critical = [
    "jellyfin"
    "podman-tdarr-server"
    "scrutiny"
    "adguardhome"
    "unbound"
    "nfs-server"
  ];
  alertFor = name: {
    "${name}".unitConfig.OnFailure = [ "ntfy-on-failure@%n.service" ];
  };
in
{
  systemd.services = lib.mkMerge (map alertFor critical);
}
