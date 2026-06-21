{ pkgs, ... }:

let
  tailnetIP = "100.92.76.121";
in
{
  systemd.services.create-it-tools-network = {
    description = "Create it-tools podman network (no DNS)";
    wantedBy = [ "podman-it-tools.service" ];
    before   = [ "podman-it-tools.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists it-tools-net || \
        ${pkgs.podman}/bin/podman network create --disable-dns it-tools-net
    '';
  };

  virtualisation.oci-containers.containers.it-tools = {
    image = "ghcr.io/sharevb/it-tools:latest";
    ports = [ "${tailnetIP}:8085:80" ];
    extraOptions = [ "--network=it-tools-net" ];
  };

  systemd.services.podman-it-tools.after = [ "create-it-tools-network.service" ];
}
