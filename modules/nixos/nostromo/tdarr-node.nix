{ lib, ... }:

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
    # Throttle so simultaneous transcode jobs can't starve gameplay/desktop.
    # Each ffmpeg worker can peg a core (saw 240% CPU + 6MB/s sustained disk),
    # which caused 10-20s stalls in Mordhau/BattleBit. Cap CPU + give the
    # game/desktop IO priority. tdarr will transcode slower but won't compete.
    serviceConfig = {
      CPUQuota          = "400%";   # max 4 of 12 threads
      CPUWeight         = 20;       # default 100, lower = less scheduler share under contention
      Nice              = 19;       # absolute lowest CPU priority
      IOWeight          = 50;       # half default IO bandwidth
      IOSchedulingClass = "idle";   # only get IO when nothing else wants it
      # Give ffmpeg jobs 5s to flush, then SIGKILL. Without this, `tdarr-off`
      # hangs ~90-120s waiting for in-flight transcodes. Jobs are checkpointed
      # by tdarr-server and will resume on next start. mkForce because
      # oci-containers default is 120s.
      TimeoutStopSec    = lib.mkForce "5s";
    };
  };
}
