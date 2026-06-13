{ ... }:

{
  home.shellAliases = {
    rebuild   = "nh os switch ~/dotfiles";
    clean     = "nh clean all";
    update    = "nix flake update ~/dotfiles";
    secrets   = "sudo SOPS_AGE_KEY_FILE=/persist/secrets/age/keys.txt sops ~/dotfiles/secrets/secrets.yaml";
    eq-music  = "easyeffects --load-preset music";
    eq-gaming = "easyeffects --load-preset gaming";
    eq-movies = "easyeffects --load-preset movies";
    eq-flat   = "easyeffects --load-preset flat";
    eq-night  = "easyeffects --load-preset night";
    eq-voice  = "easyeffects --load-preset voice";
    deploy-ishimura = "colmena apply --on ishimura";
    deploy-normandy = "colmena apply --on normandy";
    deploy-all = "colmena apply";
    ishimura  = "TERM=xterm-256color ssh -p 36475 maxwell@192.168.254.186";
    normandy  = "TERM=xterm-256color ssh -p 36475 maxwell@100.108.98.70";

    # Service restarts on ishimura
    restart-jellyfin   = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart jellyfin";
    restart-tdarr      = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-tdarr-server";
    restart-scrutiny   = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart scrutiny";

    # Service restarts on normandy
    restart-traefik    = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-traefik";
    restart-voidauth   = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-voidauth";
    restart-anubis     = "ssh -t -p 36475 maxwell@100.108.98.70 'sudo systemctl restart anubis-public anubis-homepage'";
    restart-homepage   = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-homepage";

    # Quick health check across the public stack
    health-check = ''for u in https://ishimura.lol https://auth.ishimura.lol https://jellyfin.ishimura.lol http://ishimura:8265 http://ishimura:47890; do printf "%-40s " "$u"; curl -kIso /dev/null -w "%{http_code}\n" "$u" --max-time 5; done'';
  };
}
