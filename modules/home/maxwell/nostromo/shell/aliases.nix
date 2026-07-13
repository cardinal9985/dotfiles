{ ... }:

{
  home.shellAliases = {
    rebuild = "nh os switch ~/dotfiles";
    claude = "claude --dangerously-skip-permissions";
    clean = "nh clean all -k 3";
    gc = "nh clean all -k 5";
    update = "nix flake update ~/dotfiles";
    secrets = "sudo SOPS_AGE_KEY_FILE=/persist/secrets/age/keys.txt sops ~/dotfiles/secrets/secrets.yaml";
    eq-music = "easyeffects --load-preset music";
    eq-gaming = "easyeffects --load-preset gaming";
    eq-movies = "easyeffects --load-preset movies";
    eq-flat = "easyeffects --load-preset flat";
    eq-night = "easyeffects --load-preset night";
    eq-voice = "easyeffects --load-preset voice";
    fix-nostromo = "systemctl --failed --no-legend | awk '{print $1}' | xargs -r sudo systemctl restart";
    fix-ishimura = ''ssh -t -p 36475 maxwell@192.168.254.186 "systemctl --failed --no-legend | awk '{print \$1}' | xargs -r sudo systemctl restart"'';
    fix-normandy = ''ssh -t -p 36475 maxwell@100.108.98.70 "systemctl --failed --no-legend | awk '{print \$1}' | xargs -r sudo systemctl restart"'';
    fix-all = ''fix-nostromo; ssh -t -p 36475 maxwell@192.168.254.186 "systemctl --failed --no-legend | awk '{print \$1}' | xargs -r sudo systemctl restart"; ssh -t -p 36475 maxwell@100.108.98.70 "systemctl --failed --no-legend | awk '{print \$1}' | xargs -r sudo systemctl restart"'';
    deploy-ishimura = ''colmena apply --on ishimura && curl -s -H "X-Title: Deploy ishimura ✓" -H "X-Tags: rocket" -d "ok" http://normandy:8080/deploy || curl -s -H "X-Title: Deploy ishimura ✗" -H "X-Priority: high" -H "X-Tags: x" -d "failed" http://normandy:8080/deploy'';
    deploy-normandy = ''colmena apply --on normandy && curl -s -H "X-Title: Deploy normandy ✓" -H "X-Tags: rocket" -d "ok" http://normandy:8080/deploy || curl -s -H "X-Title: Deploy normandy ✗" -H "X-Priority: high" -H "X-Tags: x" -d "failed" http://normandy:8080/deploy'';
    deploy-all = ''colmena apply --on ishimura,normandy && curl -s -H "X-Title: Deploy all ✓" -H "X-Tags: rocket" -d "ok" http://normandy:8080/deploy || curl -s -H "X-Title: Deploy all ✗" -H "X-Priority: high" -H "X-Tags: x" -d "failed" http://normandy:8080/deploy'';
    ishimura = "TERM=xterm-256color ssh -p 36475 maxwell@192.168.254.186";
    normandy = "TERM=xterm-256color ssh -p 36475 maxwell@100.108.98.70";
    # ── ishimura ────────────────────────────────────────────────────────
    restart-jellyfin = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart jellyfin";
    restart-navidrome = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart navidrome";
    restart-tdarr = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-tdarr-server";
    restart-scrutiny = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart scrutiny";
    restart-slskd = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-slskd";
    restart-romm = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-romm";
    restart-booklore = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-booklore";
    restart-refinery = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart ishimura-refinery";
    restart-stats = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart ishimura-stats";
    restart-requests = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart ishimura-requests";
    restart-rec-room = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart ishimura-rec-room";
    restart-dicebear = "ssh -t -p 36475 maxwell@192.168.254.186 'sudo systemctl restart podman-dicebear-api podman-dicebear-www'";
    restart-it-tools = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-it-tools";
    restart-filebrowser = "ssh -t -p 36475 maxwell@192.168.254.186 sudo systemctl restart podman-filebrowser";
    tdarr-off = "sudo systemctl stop podman-tdarr-node";
    tdarr-on = "sudo systemctl start podman-tdarr-node";
    # ── normandy ────────────────────────────────────────────────────────
    restart-traefik = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-traefik";
    restart-pangolin = "ssh -t -p 36475 maxwell@100.108.98.70 'sudo systemctl restart podman-pangolin podman-gerbil'";
    restart-voidauth = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-voidauth";
    restart-anubis = "ssh -t -p 36475 maxwell@100.108.98.70 'sudo systemctl restart anubis-public anubis-homepage'";
    restart-searxng = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-searxng";
    restart-synctube = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-synctube";
    restart-homepage = "ssh -t -p 36475 maxwell@100.108.98.70 sudo systemctl restart podman-homepage";
    # ── nostromo ────────────────────────────────────────────────────────
    restart-hangar = "sudo systemctl restart hangar";
    restart-kf2 = "sudo systemctl restart kf2";
    restart-vs = "sudo systemctl restart vintagestory";
    restart-tarkov = "sudo systemctl restart tarkov-spt";
    health-check = ''for u in https://ishimura.lol https://auth.ishimura.lol https://jellyfin.ishimura.lol http://ishimura:8265 http://ishimura:47890; do printf "%-40s " "$u"; curl -kIso /dev/null -w "%{http_code}\n" "$u" --max-time 5; done'';
    # Clear stale Hive lock after cake_wallet exits uncleanly so it can start again.
    cake-fix = "pkill -x cake_wallet; rm -f ~/.config/cake_wallet/*.lock";
  };
}
