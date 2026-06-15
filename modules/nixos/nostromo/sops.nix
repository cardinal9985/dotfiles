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
      # Backup SSH key. Daily key lives in gpg-agent (use `ssh-add -L`).
      # Materialized at /run/secrets/ssh/maxwell_private_key so it does
      # NOT shadow the gpg-agent identity at ~/.ssh/id_ed25519.
      "ssh/maxwell_private_key" = {
        owner = "maxwell";
        group = "users";
        mode  = "0400";
      };
    };
  };
}
