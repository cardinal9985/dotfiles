{ lib, ... }:

let
  critical = [
    "podman-tdarr-node"
  ];
  alertFor = name: {
    "${name}".unitConfig.OnFailure = [ "ntfy-on-failure@%n.service" ];
  };
in
{
  systemd.services = lib.mkMerge (map alertFor critical);
}
