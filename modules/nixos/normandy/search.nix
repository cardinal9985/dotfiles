{ config, pkgs, ... }:

let
  valkeyIP   = "10.89.70.10";
  searxngIP  = "10.89.70.11";
  searxngURL = "http://${searxngIP}:8080";

  themeJson = pkgs.writeText "degoog-theme.json" (builtins.toJSON {
    name        = "Ishimura";
    author      = "maxwell";
    description = "Dead Space-themed search interface.";
    css         = "style.css";
  });

  themeStyle = pkgs.writeText "degoog-style.css" ''
    * {
      font-family: system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    }

    :root {
      --primary: #4285f4;
      --primary-hover: #5a95f5;
      --primary-rgb: 66, 133, 244;
      --danger: #ea4335;
      --warning: #fbbc05;
      --success: #34a853;
      --bg: #1f1f1f;
      --bg-light: #303134;
      --bg-hover: #3c4043;
      --border: #5f6368;
      --border-light: #444746;
      --text-primary: #e8eaed;
      --text-secondary: #80868b;
      --text-link: #99c3ff;
      --text-link-visited: #c58af9;
      --text-cite: #bdc1c6;
      --text-snippet: #bdc1c6;
      --search-bar-bg: #4d5156;
      --search-bar-bg-hover: #5f6368;
      --search-bar-focused: #303134;
      --search-bar-icon: #e8e8e8;
      --btn-bg: #303134;
      --btn-text: #e8eaed;
      --overlay-bg: rgba(0, 0, 0, 0.6);
      --white: #fff;
    }

    @media (prefers-color-scheme: light) {
      :root:not([data-theme=dark]) {
        --bg: #fff;
        --bg-light: #f8f9fa;
        --bg-hover: #e8eaed;
        --border: #dadce0;
        --border-light: #d2d2d2;
        --text-primary: #202124;
        --text-secondary: #70757a;
        --text-link: #1a0dab;
        --text-link-visited: #681da8;
        --text-cite: #202124;
        --text-snippet: #4d5156;
        --search-bar-bg: #ebebeb;
        --search-bar-bg-hover: #ebebeb;
        --search-bar-focused: white;
        --search-bar-icon: #1f1f1f;
        --btn-bg: #f8f9fa;
        --btn-text: #3c4043;
        --overlay-bg: rgba(0, 0, 0, 0.4);
      }
    }

    [data-theme=light] {
      --bg: #fff;
      --bg-light: #f8f9fa;
      --bg-hover: #e8eaed;
      --border: #dadce0;
      --border-light: #d2d2d2;
      --text-primary: #202124;
      --text-secondary: #70757a;
      --text-link: #1a0dab;
      --text-link-visited: #681da8;
      --text-cite: #202124;
      --text-snippet: #4d5156;
      --search-bar-bg: #ebebeb;
      --search-bar-bg-hover: #ebebeb;
      --search-bar-focused: white;
      --search-bar-icon: #1f1f1f;
      --btn-bg: #f8f9fa;
      --btn-text: #3c4043;
      --overlay-bg: rgba(0, 0, 0, 0.4);
    }

    [data-theme=dark] {
      --bg: #1f1f1f;
      --bg-light: #303134;
      --bg-hover: #3c4043;
      --border: #5f6368;
      --border-light: #444746;
      --text-primary: #e8eaed;
      --text-secondary: #80868b;
      --text-link: #99c3ff;
      --text-link-visited: #c58af9;
      --text-cite: #bdc1c6;
      --text-snippet: #bdc1c6;
      --search-bar-bg: #4d5156;
      --search-bar-bg-hover: #5f6368;
      --search-bar-focused: #303134;
      --search-bar-icon: #e8e8e8;
      --btn-bg: #303134;
      --btn-text: #e8eaed;
      --overlay-bg: rgba(0, 0, 0, 0.6);
    }

    .results-search-bar,
    .search-bar,
    .search-input {
      font-weight: 100;
      height: 50px;
    }

    .search-input { color: #ffffff !important; caret-color: #ffffff; }
    [data-theme="light"] .search-input { color: #202124 !important; caret-color: #202124; }

    #btn-search { font-size: 0 !important; }
    #btn-search::before { content: "Search"; font-size: 1rem; font-weight: 500; }

    .results-search-bar:has(.search-input:focus),
    .search-bar:has(.search-input:focus) {
      background: var(--search-bar-focused);
    }

    [data-theme="light"] .results-search-bar,
    [data-theme="light"] .search-bar {
      background: var(--bg);
      border: 1px solid var(--border);
      box-shadow: 0px 3px 10px 0px rgba(31, 31, 31, 0.08);
    }

    [data-theme="light"] .results-search-bar:hover,
    [data-theme="light"] .search-bar:hover {
      box-shadow: 0 2px 8px 1px rgba(64, 60, 67, .24);
    }

    .ac-dropdown {
      border-top: 1px solid #5f6368;
      background: var(--search-bar-focused);
    }

    [data-theme="light"] .ac-dropdown {
      border-top: 1px solid #e8eaed;
      box-shadow: 0 6px 8px 1px rgba(64, 60, 67, .24);
    }

    .search-btn {
      border-radius: 8px;
      font-weight: 500;
    }

    #home-footer a {
      color: white;
      font-size: 14px;
    }

    .footer {
      border-top: 1px solid #444746;
      background: #171717;
    }

    [data-theme="light"] .footer {
      border-top: 1px solid #d2d2d2;
      background: #f2f2f2;
    }

    [data-theme="light"] #home-footer a { color: black; }

    #results-header {
      background: var(--bg);
      position: sticky;
      z-index: 1;
      top: 0;
    }

    #results-header.scrolled { padding-bottom: 18px; }

    [data-theme="light"] #results-header.scrolled {
      border-bottom: 1px solid var(--border-light);
    }

    .btn { border-radius: 8px; user-select: none; }
    .btn--secondary { background: var(--btn-bg); }
    .btn--secondary:hover { background: var(--bg-hover); }

    .glance-link { color: var(--text-link) !important; }

    .wiki-desc {
      letter-spacing: 0 !important;
      text-transform: none !important;
    }

    .sidebar-panel,
    .results-slot-panel { border-radius: 20px !important; border: none; }

    .results-tab { font-weight: 500; }
    .glance-box { margin: 0; border-radius: 20px; }
    .result-title { margin-top: 10px; }
    .result-url-row { gap: 12px; }
    .result-favicon { border: 1px solid var(--border-light); }

    .result-engine-tag {
      user-select: none;
      font-size: 12px;
      color: var(--text-link);
      border: 1px solid var(--border-light);
      background: var(--bg);
      border-radius: 999px;
      padding: 6px 12px;
    }

    .result-engine-tag:hover {
      color: var(--text-primary);
      background: var(--bg-light);
      border-color: var(--bg-hover);
    }

    .sidebar-accordion-body:has(.wiki-card),
    .sidebar-accordion-body:has(.kp-title),
    .sidebar-accordion-body:has(.kp-description),
    .sidebar-accordion-body:has(.kp-image) {
      background: var(--bg-light);
      margin: 20px;
    }

    .sidebar-accordion-body { background: var(--bg); padding: 0; }

    .engine-stat-row {
      border-radius: 4px;
      background: var(--bg-light);
      padding: 14px;
      margin-bottom: 2px;
    }

    .related-search-link {
      padding: 14px;
      border-bottom: 0;
      margin-bottom: 2px;
      font-size: 14px;
      background: var(--bg-light);
      border-radius: 4px;
    }

    .btn { border-radius: 999px; }
    .toggle-slider::after { border: none; }
    .settings-tab-select { border-radius: 999px; }
    [data-theme="light"] .settings-page-body { background: #f0f4f9; }
    .settings-nav-item { border-radius: 999px; }
    .settings-nav-item.active { box-shadow: none; border: none; font-weight: normal; }
    .settings-nav-search { border-radius: 999px; }
    [data-theme="light"] .settings-nav-item.active { background: white; }
    .ext-group-label { text-transform: capitalize; }

    .store-updates-body,
    .settings-fieldset,
    .ext-cards { gap: 2px; }

    .store-updates-row { padding: 17px; border-radius: 4px; background: var(--bg); }

    .ext-card:not(.settings-section) {
      padding: 17px;
      border: none;
      border-radius: 4px;
      background: #37393b;
    }

    .settings-section:not(.store-catalog-section) {
      border-radius: 25px;
      box-shadow: none;
      background: none;
      border: none;
      padding: 0;
      margin: 0 0 2rem;
    }

    .settings-toggle-wrap:not(.settings-desc) {
      flex-direction: row-reverse;
      justify-content: space-between;
    }

    .settings-toggle-wrap { background: #37393b; padding: 17px; border: none; }

    [data-theme="light"] .store-updates-row,
    [data-theme="light"] .settings-toggle-wrap,
    [data-theme="light"] .ext-card:not(.settings-section):not(.settings-desc) { background: white; }

    .ext-card-configure,
    .ext-card-apply { background: #282a2c; border-radius: 999px; border: none; }

    [data-theme="light"] .ext-card-configure,
    [data-theme="light"] .ext-card-apply { color: black; background: #d5dff0; }

    .theme-select { background: var(--search-bar-bg); border-radius: 999px; padding: 15px; border: none; }

    /* ── Ishimura overrides ── */

    #home-logo > * { display: none !important; }
    #home-logo {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
    }
    #home-logo::before {
      content: "ISHIMURA";
      font-family: 'Courier New', Courier, monospace;
      font-size: 3rem;
      font-weight: bold;
      letter-spacing: 0.5em;
      padding-left: 0.5em;
      color: var(--primary);
      display: block;
      text-align: center;
    }
    #home-logo::after {
      content: "[ USG ISHIMURA ]";
      font-family: 'Courier New', Courier, monospace;
      font-size: 0.65rem;
      letter-spacing: 0.3em;
      color: var(--text-secondary);
      display: block;
      text-align: center;
    }

    .results-logo > * { display: none !important; }
    .results-logo {
      text-decoration: none;
      font-family: 'Courier New', Courier, monospace;
      font-size: 1rem;
      font-weight: bold;
      letter-spacing: 0.25em;
      color: var(--primary);
    }
    .results-logo::before { content: "ISHIMURA"; }
  '';

  pluginSettings = pkgs.writeText "degoog-plugin-settings.json" (builtins.toJSON {
    theme."active" = "ishimura";
    "searxng-search"."baseUrl" = searxngURL;
    "searxng-images"."baseUrl" = searxngURL;
    "searxng-videos"."baseUrl" = searxngURL;
    "searxng-news"."baseUrl"   = searxngURL;
    "searxng-file"."baseUrl"   = searxngURL;
  });
in
{
  systemd.tmpfiles.rules = [
    "d /persist/searxng        0755 977  977  -"
    "d /persist/searxng/data   0750 977  977  -"
    "d /persist/searxng/valkey 0750 999  1000 -"
    "d /persist/degoog         0755 1000 1000 -"
    "d /persist/degoog/data    0755 1000 1000 -"
  ];

  systemd.services.create-searxng-network = {
    description = "Create searxng podman network (no DNS, static subnet)";
    wantedBy = [ "podman-searxng.service" "podman-searxng-valkey.service" "podman-degoog.service" ];
    before   = [ "podman-searxng.service" "podman-searxng-valkey.service" "podman-degoog.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists searxng-net || \
        ${pkgs.podman}/bin/podman network create \
          --disable-dns \
          --subnet=10.89.70.0/24 \
          searxng-net
    '';
  };

  sops.templates."searxng-settings.yml" = {
    mode = "0444";
    content = ''
      use_default_settings: true
      general:
        instance_name: "USG Ishimura"
        privacypolicy_url: false
        donation_url: false
        contact_url: false
        enable_metrics: true
      server:
        port: 8080
        bind_address: "0.0.0.0"
        base_url: https://search.ishimura.lol/
        secret_key: "${config.sops.placeholder."searxng/secret_key"}"
        limiter: false
        image_proxy: true
        method: "POST"
        public_instance: false
        default_http_headers:
          X-Content-Type-Options: nosniff
          X-Download-Options: noopen
          X-Robots-Tag: noindex, nofollow
          Referrer-Policy: no-referrer
      valkey:
        url: valkey://${valkeyIP}:6379/0
      search:
        safe_search: 0
        autocomplete: duckduckgo
        formats:
          - html
          - json
      ui:
        static_use_hash: true
        default_theme: simple
        theme_args:
          simple_style: dark
        infinite_scroll: false
      enabled_plugins:
        - 'Hash plugin'
        - 'Search on category select'
        - 'Self Informations'
        - 'Tracker URL remover'
        - 'Unit converter plugin'
    '';
  };

  virtualisation.oci-containers.containers = {
    searxng-valkey = {
      image = "docker.io/valkey/valkey:8-alpine";
      cmd = [
        "valkey-server"
        "--save" "30" "1"
        "--loglevel" "warning"
      ];
      volumes = [ "/persist/searxng/valkey:/data" ];
      extraOptions = [
        "--network=searxng-net"
        "--ip=${valkeyIP}"
      ];
    };

    searxng = {
      image = "docker.io/searxng/searxng:latest";
      environment.TZ = "America/New_York";
      volumes = [
        "${config.sops.templates."searxng-settings.yml".path}:/etc/searxng/settings.yml:ro"
        "/persist/searxng/data:/var/cache/searxng"
      ];
      ports = [ "127.0.0.1:8888:8080" ];
      extraOptions = [
        "--network=searxng-net"
        "--ip=${searxngIP}"
      ];
      dependsOn = [ "searxng-valkey" ];
    };

    degoog = {
      image   = "ghcr.io/degoog-org/degoog:latest";
      volumes = [ "/persist/degoog/data:/app/data" ];
      ports   = [ "127.0.0.1:4444:4444" ];
      environment.TZ = "America/New_York";
      extraOptions   = [ "--network=searxng-net" ];
    };
  };

  systemd.services.podman-degoog.after        = [ "create-searxng-network.service" ];
  systemd.services.podman-searxng.after        = [ "create-searxng-network.service" ];
  systemd.services.podman-searxng-valkey.after = [ "create-searxng-network.service" ];

  system.activationScripts.degoog-config = {
    deps = [];
    text = ''
      base=/persist/degoog/data
      install -d -m 0755 -o 1000 -g 1000 "$base"
      install -d -m 0755 -o 1000 -g 1000 "$base/themes/ishimura"

      install -m 0644 -o 1000 -g 1000 ${themeJson}  "$base/themes/ishimura/theme.json"
      install -m 0644 -o 1000 -g 1000 ${themeStyle} "$base/themes/ishimura/style.css"

      if [ ! -f "$base/plugin-settings.json" ]; then
        install -m 0644 -o 1000 -g 1000 ${pluginSettings} "$base/plugin-settings.json"
      fi
    '';
  };
}
