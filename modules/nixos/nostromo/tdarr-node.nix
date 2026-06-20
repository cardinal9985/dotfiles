{ ... }:

{
  hardware.nvidia-container-toolkit.enable = true;

  environment.persistence."/persist".directories = [
    { directory = "/persist/tdarr-node";         user = "maxwell"; group = "users"; mode = "0755"; }
    { directory = "/persist/tdarr-node/configs"; user = "maxwell"; group = "users"; mode = "0755"; }
    { directory = "/persist/tdarr-node/logs";    user = "maxwell"; group = "users"; mode = "0755"; }
  ];

  virtualisation.oci-containers.containers.tdarr-node = {
    image = "ghcr.io/haveagitgat/tdarr_node@sha256:9ee77dc5c2e3d4a488f9bd3a057031abfa443a91d92800fd244cbd0adc35c06f";

    environment = {
      TZ = "America/New_York";
      PUID = "1000";
      PGID = "100";
      UMASK_SET = "002";
      nodeName = "Nostromo-NVENC";
      serverIP = "100.92.76.121";
      serverPort = "8266";
      inContainer = "true";
      NVIDIA_DRIVER_CAPABILITIES = "video,compute";
      NVIDIA_VISIBLE_DEVICES = "all";
    };

    volumes = [
      "/persist/tdarr-node/configs:/app/configs"
      "/persist/tdarr-node/logs:/app/logs"
      "/mnt/storage/tdarr-cache:/temp"
      "/mnt/storage:/media"
    ];

    extraOptions = [
      "--device=nvidia.com/gpu=all"
    ];
  };

  systemd.services.podman-tdarr-node = {
    after = [ "mnt-storage.automount" ];
    requires = [ "mnt-storage.automount" ];
  };
}
