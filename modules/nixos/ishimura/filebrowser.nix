{ pkgs, config, ... }:

# FileBrowser Quantum (gtsteffaniak/filebrowser fork) - modernized web file
# manager for /mnt/storage. Lets us manage media library + mod bundles + any
# other shared files through a UI instead of scp.
#
# Auth: double-gated at Pangolin (voidauth + tailnet-only). FileBrowser also
# has its own admin user as a defense-in-depth layer.
#
# Sees the same /mnt/storage/mods folder that mods-server.nix exposes
# publicly, so dropping a new mod zip via the UI immediately makes it
# downloadable at ishimura.lol/mods/<game>/file.zip.

let
  configYaml = pkgs.writeText "filebrowser-config.yml" ''
    server:
      port: 80
      baseURL: "/"
      database: "/config/filebrowser.db"
      logging:
        - levels: "info|warning|error"
          apiLevels: "warning|error"

    # Single source root - the full ishimura storage. Quantum can index
    # multiple sources, but one is enough for now.
    sources:
      - path: "/data"
        name: "ishimura-storage"
        config:
          createUserDir: false
          defaultUserScope: "/"
          defaultEnabled: true

    auth:
      tokenExpirationHours: 168
      methods:
        password:
          enabled: true
          signup: false
          minLength: 12
        noauth: false

    frontend:
      name: "ISHIMURA STORAGE"
      disableUsedPercentage: false
      # Inject custom CSS to push toward the Dead Space terminal aesthetic.
      # Quantum supports an externalUrl for additional stylesheet; the
      # busybox-served /mods static doesn't reach this container, so we
      # bake the CSS into a volume below.
      externalLinks:
        - text: "Back to ishimura.lol"
          url: "https://ishimura.lol"

    integrations:
      media:
        ffmpegPath: "/usr/local/bin"
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

  # Render config + branding CSS at activation time.
  system.activationScripts.filebrowser-config = ''
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

    ports = [ "100.92.76.121:8088:80" ];
  };

  systemd.services.podman-filebrowser = {
    after = [ "mnt-storage.automount" ];
    requires = [ "mnt-storage.automount" ];
  };
}
