{ ... }:

{
  # NVIDIA Container Toolkit + CDI for podman GPU passthrough.
  # Lets the Tdarr worker invoke NVENC/NVDEC for hardware-accelerated
  # transcoding via the dGPU.
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
      # ishimura tailnet IP. Worker connects to server on port 8266.
      serverIP = "100.92.76.121";
      serverPort = "8266";
      inContainer = "true";
      # `all` includes the `utility` capability which mounts host nvidia-smi
      # into the container. Host's nvidia-smi is linked against host glibc;
      # container's glibc is older. Result: symbol lookup error every time
      # Tdarr probes the GPU (cosmetic but log spam).
      # `video,compute` is enough for NVENC/NVDEC. Tdarr falls back to ffmpeg
      # encoder probes when nvidia-smi is missing, which is what we want.
      NVIDIA_DRIVER_CAPABILITIES = "video,compute";
      NVIDIA_VISIBLE_DEVICES = "all";
    };
    volumes = [
      "/persist/tdarr-node/configs:/app/configs"
      "/persist/tdarr-node/logs:/app/logs"
      # Shared transcode cache on ishimura's NFS export. Server reads worker
      # output here for mediaInfo + replace-original post-steps. Distinct
      # workDir name per job (tdarr-workDirN-XXX) avoids cross-node collisions.
      "/mnt/storage/tdarr-cache:/temp"
      # NFS mount from ishimura over tailnet. Worker reads source files
      # and writes transcoded output to the same shared filesystem,
      # avoiding any copy step.
      "/mnt/storage:/media"
    ];
    extraOptions = [
      # CDI device passthrough for NVIDIA GPU. Requires
      # hardware.nvidia-container-toolkit.enable.
      "--device=nvidia.com/gpu=all"
    ];
  };

  # Tdarr node systemd unit must wait until the NFS automount has fired,
  # otherwise the worker starts with an empty /media and errors on every job.
  systemd.services.podman-tdarr-node = {
    after = [ "mnt-storage.automount" ];
    requires = [ "mnt-storage.automount" ];
  };
}
