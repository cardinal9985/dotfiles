{ inputs, config, ... }:

{
  imports = [ inputs.bridge.nixosModules.collector ];

  sops.secrets."bridge/collector_token" = {
    owner = "bridge-collector";
    mode = "0400";
  };

  services.bridge-collector = {
    enable = true;
    tokenFile = config.sops.secrets."bridge/collector_token".path;
  };
}
