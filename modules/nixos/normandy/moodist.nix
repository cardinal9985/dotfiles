{ ... }:

{
  virtualisation.oci-containers.containers.moodist = {
    image = "ghcr.io/remvze/moodist:latest";
    ports = [ "127.0.0.1:4546:8080" ];
  };
}
