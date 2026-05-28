{ ... }:

{
  home.shellAliases = {
    rebuild = "nh os switch ~/dotfiles";
    clean = "nh clean all";
    secrets = "sudo SOPS_AGE_KEY_FILE=/persist/secrets/age/keys.txt sops ~/dotfiles/secrets/secrets.yaml";
  };
}
