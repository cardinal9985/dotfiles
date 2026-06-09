{ pkgs, ... }:

let
  models = [
    "llama3.1:8b"
    "qwen2.5-coder:7b"
  ];
in
{
  virtualisation.oci-containers.containers.ollama = {
    image = "ollama/ollama:latest";
    autoStart = true;

    ports = [ "127.0.0.1:11434:11434" ];

    volumes = [
      "/persist/var/lib/ollama:/root/.ollama"
    ];

    extraOptions = [
      "--device=nvidia.com/gpu=all"
      "--network=ai"
    ];
  };

  systemd.services.ollama-pull-models = {
    description = "Pull configured Ollama models";
    after = [ "podman-ollama.service" ];
    wants = [ "podman-ollama.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      Restart = "on-failure";
      RestartSec = "5s";
    };
    script = builtins.concatStringsSep "\n"
      (map (model: "${pkgs.podman}/bin/podman exec ollama ollama pull ${model}") models);
  };

  virtualisation.oci-containers.containers.open-webui = {
    image = "ghcr.io/open-webui/open-webui:main";
    autoStart = true;
    dependsOn = [ "ollama" ];

    ports = [ "127.0.0.1:8080:8080" ];

    volumes = [
      "/persist/var/lib/open-webui:/app/backend/data"
    ];

    environment = {
      OLLAMA_BASE_URL = "http://ollama:11434";
      SCARF_NO_ANALYTICS = "true";
      DO_NOT_TRACK = "true";
      ANONYMIZED_TELEMETRY = "false";
      WEBUI_AUTH = "false";
    };

    extraOptions = [
      "--network=ai"
    ];
  };

  systemd.services.podman-network-ai = {
    description = "Create podman network for AI services";
    before = [ "podman-ollama.service" "podman-open-webui.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = "${pkgs.podman}/bin/podman network create ai 2>/dev/null || true";
  };

  environment.systemPackages = with pkgs; [
    claude-code
    alpaca
    opencode
  ];
}
