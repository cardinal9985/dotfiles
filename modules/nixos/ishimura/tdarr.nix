{ ... }:

let
  tailnetIP = "100.92.76.121";  # ishimura tailnet IP
in
{
  systemd.tmpfiles.rules = [
    "d /persist/tdarr          0755 maxwell users -"
    "d /persist/tdarr/server   0755 maxwell users -"
    "d /persist/tdarr/configs  0755 maxwell users -"
    "d /persist/tdarr/logs     0755 maxwell users -"
    # Shared transcode cache on the mergerfs union, NFS-exported to nostromo.
    # Both tdarr-server (here) and tdarr-node (nostromo) mount this as /temp
    # so the server can read worker output to run mediaInfo + replace-original.
    "d /mnt/storage/tdarr-cache  0755 maxwell users -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/tdarr"; user = "maxwell"; group = "users"; mode = "0755"; }
  ];

  virtualisation.oci-containers.containers.tdarr-server = {
    image = "ghcr.io/haveagitgat/tdarr@sha256:61af2de3245dc71da0038f80452eb2d3b960a2f76634ded108227c6ba293aee2";
    environment = {
      TZ = "America/New_York";
      PUID = "1000";
      PGID = "100";
      UMASK_SET = "002";
      serverIP = "0.0.0.0";
      serverPort = "8266";
      webUIPort = "8265";
      # No internal worker on the server: ishimura's iGPU is reserved for
      # Jellyfin's live transcoding. Heavy lifting happens on nostromo.
      internalNode = "false";
      inContainer = "true";
    };
    volumes = [
      "/persist/tdarr/server:/app/server"
      "/persist/tdarr/configs:/app/configs"
      "/persist/tdarr/logs:/app/logs"
      # Shared with nostromo's tdarr-node via NFS so the server can see the
      # worker's output cache for mediaInfo + replace-original post-steps.
      "/mnt/storage/tdarr-cache:/temp"
      "/mnt/storage:/media"
    ];
    ports = [
      # Web UI bound to tailnet IP only. Traefik on Normandy proxies in via
      # tdarr.ishimura.lol with tailnet-only IPAllowList middleware.
      "${tailnetIP}:8265:8265"
      # Node API bound to tailnet IP. nostromo's worker connects here.
      "${tailnetIP}:8266:8266"
    ];
  };
}
