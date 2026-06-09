{ ... }:

{
  home.shellAliases = {
    rebuild  = "nh os switch ~/dotfiles";
    clean    = "nh clean all";
    update   = "nix flake update ~/dotfiles";
    secrets  = "sudo SOPS_AGE_KEY_FILE=/persist/secrets/age/keys.txt sops ~/dotfiles/secrets/secrets.yaml";
    eq-music  = "easyeffects --load-preset music";
    eq-gaming = "easyeffects --load-preset gaming";
    eq-movies = "easyeffects --load-preset movies";
    eq-flat   = "easyeffects --load-preset flat";
    eq-night  = "easyeffects --load-preset night";
    eq-voice  = "easyeffects --load-preset voice";
  };
}
