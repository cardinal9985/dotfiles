{ pkgs, ... }:

let
  tailnetIP = "100.92.76.121";  # ishimura
  src = ../../../config/dicebear;

  # Build the customizer page tree with Nix (mirrors how homepage.nix does it).
  # Add more files here as the customizer grows.
  customizer = pkgs.runCommand "dicebear-customizer" {} ''
    mkdir -p $out
    cp ${src}/index.html $out/index.html
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/dicebear     0755 maxwell users -"
    "d /persist/dicebear/www 0755 maxwell users -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/dicebear"; user = "maxwell"; group = "users"; mode = "0755"; }
  ];

  system.activationScripts.dicebear-customizer = ''
    ${pkgs.rsync}/bin/rsync -a --delete ${customizer}/ /persist/dicebear/www/
    chmod -R a+rX /persist/dicebear/www
  '';

  # Same AGH-conflict workaround as the other ishimura podman containers.
  systemd.services.create-dicebear-network = {
    description = "Create dicebear podman network (no DNS)";
    wantedBy = [ "podman-dicebear-api.service" "podman-dicebear-www.service" ];
    before   = [ "podman-dicebear-api.service" "podman-dicebear-www.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists dicebear-net || \
        ${pkgs.podman}/bin/podman network create --disable-dns dicebear-net
    '';
  };

  virtualisation.oci-containers.containers = {
    # DiceBear self-hosted HTTP API. Generates SVG/PNG avatars from a seed,
    # endpoints like /10.x/{style}/svg?seed=maxwell&... .
    dicebear-api = {
      image = "docker.io/dicebear/api:4";
      ports = [ "${tailnetIP}:7373:3000" ];
      extraOptions = [ "--network=dicebear-net" ];
    };

    # Static customizer page served by busybox httpd, content built by Nix
    # above and rsynced to /persist/dicebear/www.
    dicebear-www = {
      image = "docker.io/library/busybox:latest";
      cmd = [ "httpd" "-f" "-p" "80" "-h" "/srv" ];
      volumes = [ "/persist/dicebear/www:/srv:ro" ];
      ports = [ "${tailnetIP}:7374:80" ];
      extraOptions = [ "--network=dicebear-net" ];
    };
  };

  systemd.services.podman-dicebear-api.after = [ "create-dicebear-network.service" ];
  systemd.services.podman-dicebear-www.after = [ "create-dicebear-network.service" ];
}
