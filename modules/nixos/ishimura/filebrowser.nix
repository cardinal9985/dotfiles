{ pkgs, config, ... }:

let

  configYaml = pkgs.writeText "filebrowser-config.yml" ''
    server:
      port: 8088
      database: "/config/filebrowser.db"
      sources:
        - path: "/data"
          name: "ishimura-storage"
  '';

  brandingCss = pkgs.writeText "filebrowser-branding.css" ''
    /* Ishimura terminal-ish accent overrides. Quantum's variables aren't
       all exposed, but these hit the most visible surfaces. */
    :root {
      --primaryColor: #fbbf60;        /* bright-yellow */
      --primaryColorAlt: #b89040;
      --accent: #6ec8e6;              /* bright-cyan */
      --textColor: #dce4f0;
      --background: #080c14;
      --surface: #0e1320;
    }
    body, .app { font-family: monospace; }
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/filebrowser         0750 1000 100 -"
    "d /persist/filebrowser/config  0750 1000 100 -"
    "d /persist/filebrowser/branding 0755 root root -"
  ];

  system.activationScripts.filebrowser-config = ''
    mkdir -p /persist/filebrowser/config /persist/filebrowser/branding
    install -m 0644 ${configYaml}    /persist/filebrowser/config/settings.yaml
    install -m 0644 ${brandingCss}   /persist/filebrowser/branding/custom.css
    chown -R 1000:100                 /persist/filebrowser/config
  '';

  virtualisation.oci-containers.containers.filebrowser = {
    image = "ghcr.io/gtsteffaniak/filebrowser:latest";

    environment = {
      TZ      = "America/New_York";
      PUID    = "1000";
      PGID    = "100";
      FILEBROWSER_CONFIG = "/config/settings.yaml";
    };

    volumes = [
      "/mnt/storage:/data"
      "/persist/filebrowser/config:/config"
      "/persist/filebrowser/branding:/branding:ro"
    ];

    extraOptions = [ "--network=host" ];
  };

  systemd.services.podman-filebrowser = {
    after = [ "mnt-storage.mount" ];
    requires = [ "mnt-storage.mount" ];
  };
}
