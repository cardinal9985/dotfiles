{ pkgs, lib, ... }:

let
  hosts           = import ../../shared/lib/hosts.nix;
  mkPodmanNetwork = import ../../shared/lib/podman-network.nix { inherit pkgs lib; };
  src             = ../../../config/dicebear;

  customizer = pkgs.runCommand "dicebear-customizer" {} ''
    mkdir -p $out
    cp ${src}/index.html $out/index.html
  '';
in
lib.mkMerge [
  (mkPodmanNetwork { name = "dicebear-net"; containers = [ "dicebear-api" "dicebear-www" ]; })
  {
    systemd.tmpfiles.rules = [
      "z /persist/dicebear     0755 maxwell users -"
      "d /persist/dicebear/www 0755 maxwell users -"
    ];

    environment.persistence."/persist".directories = [
      { directory = "/persist/dicebear"; user = "maxwell"; group = "users"; mode = "0755"; }
    ];

    system.activationScripts.dicebear-customizer = ''
      ${pkgs.rsync}/bin/rsync -a --delete ${customizer}/ /persist/dicebear/www/
      chmod -R a+rX /persist/dicebear/www
    '';

    virtualisation.oci-containers.containers = {
      dicebear-api = {
        image = "docker.io/dicebear/api:4";
        ports = [ "${hosts.ishimura.tailnet}:7373:3000" ];
        extraOptions = [ "--network=dicebear-net" ];
      };

      dicebear-www = {
        image = "docker.io/library/busybox:latest";
        cmd = [ "httpd" "-f" "-p" "80" "-h" "/srv" ];
        volumes = [ "/persist/dicebear/www:/srv:ro" ];
        ports = [ "${hosts.ishimura.tailnet}:7374:80" ];
        extraOptions = [ "--network=dicebear-net" ];
      };
    };
  }
]
