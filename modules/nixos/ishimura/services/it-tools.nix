{ pkgs, lib, ... }:

let
  hosts           = import ../../shared/lib/hosts.nix;
  mkPodmanNetwork = import ../../shared/lib/podman-network.nix { inherit pkgs lib; };
in
lib.mkMerge [
  (mkPodmanNetwork { name = "it-tools-net"; containers = [ "it-tools" ]; })
  {
    virtualisation.oci-containers.containers.it-tools = {
      image = "ghcr.io/sharevb/it-tools:latest";
      ports = [ "${hosts.ishimura.tailnet}:8085:8080" ];
      extraOptions = [ "--network=it-tools-net" ];
    };
  }
]
