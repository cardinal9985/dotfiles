{ config, inputs, ... }:
{
  imports = [ inputs.sops-nix.nixosModules.sops ];
  sops = {
    age.keyFile = "/persist/secrets/age/keys.txt";
    defaultSopsFile = ../../../secrets/secrets.yaml;
    defaultSopsFormat = "yaml";
    secrets = {
      "users/maxwell_password" = {
        neededForUsers = true;
      };
      "git/github_token" = {
        owner = "maxwell";
        group = "users";
        mode  = "0400";
      };

      "ssh/maxwell_private_key" = {
        owner = "maxwell";
        group = "users";
        mode  = "0400";
      };

      "kf2/admin_password" = {
        owner = "hangar";
        group = "hangar";
        mode  = "0400";
      };
    };
  };
}
