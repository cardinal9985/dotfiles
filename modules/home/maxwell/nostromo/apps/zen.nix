{ pkgs, config, ... }:

{
  stylix.targets.zen-browser = {
    enable = true;
    profileNames = [ "maxwell" ];
  };

  xdg.mimeApps = {
    defaultApplications = {
      "text/html" = "zen.desktop";
      "x-scheme-handler/http" = "zen.desktop";
      "x-scheme-handler/https" = "zen.desktop";
      "x-scheme-handler/about" = "zen.desktop";
      "x-scheme-handler/unknown" = "zen.desktop";
    };
  };

  # Keep links from opening in Tor or Brave
  xdg.desktopEntries = {
    brave-browser = {
      name = "Brave Web Browser";
      exec = "brave %U";
      icon = "brave-browser";
      comment = "Access the Internet";
      categories = [ "Network" "WebBrowser" ];
      mimeType = [];
    };
    "com.brave.Browser" = {
      name = "Brave Web Browser";
      exec = "brave %U";
      icon = "brave-browser";
      comment = "Access the Internet";
      categories = [ "Network" "WebBrowser" ];
      mimeType = [];
    };
    tor-browser = {
      name = "Tor Browser";
      exec = "tor-browser %U";
      icon = "tor-browser";
      comment = "Browse Anonymously";
      categories = [ "Network" "WebBrowser" ];
      mimeType = [];
    };
    torbrowser = {
      name = "Tor Browser";
      exec = "tor-browser %U";
      icon = "tor-browser";
      comment = "Browse Anonymously";
      categories = [ "Network" "WebBrowser" ];
      mimeType = [];
    };
  };

  programs.zen-browser = {
    enable = true;
    languagePacks = [ "en-US" ];

    policies = {
      DisableAccounts = true;
      DisableFirefoxAccounts = true;
      DisableFirefoxScreenshots = true;
      DisableFirefoxStudies = true;
      DisablePocket = true;
      DisableTelemetry = true;
      DontCheckDefaultBrowser = true;
      EnableTrackingProtection = {
        Cryptomining   = true;
        Fingerprinting = true;
        Locked         = true;
        Value          = true;
      };
      OverrideFirstRunPage = "";
      OverridePostUpdatePage = "";
    };

    profiles.maxwell = {
      extensions.packages = with pkgs.nur.repos.rycee.firefox-addons; [
        ublock-origin
        sponsorblock
        return-youtube-dislikes
      ];

      isDefault = true;

      settings = {
        "browser.newtabpage.enabled" = false;
        "dom.security.https_only_mode" = true;
        "extensions.autoDisableScopes" = 0;
        "privacy.donottrackheader.enabled" = true;
        "privacy.globalprivacycontrol.enabled" = true;
        "privacy.globalprivacycontrol.functionality.enabled" = true;
        "toolkit.legacyUserProfileCustomizations.stylesheets" = true;
        "toolkit.telemetry.enabled" = false;
        "geo.enabled" = false;
        "media.peerconnection.enabled" = false;
        "browser.urlbar.suggest.searches" = false;
        "network.http.referer.XOriginPolicy" = 2;
        "privacy.partition.network_state" = true;
        "browser.startup.page" = 0;

        # Privacy
        "browser.send_pings" = false;
        "browser.sessionstore.privacy_level" = 2;
        "network.dns.disablePrefetch" = true;
        "network.prefetch-next" = false;
        "beacon.enabled" = false;

        # Devtools
        "devtools.chrome.enabled" = true;
        "devtools.debugger.remote-enabled" = true;

        # Show bookmark bar
        "browser.toolbars.bookmarks.visibility" = "always";

        # Collapse extensions into unified menu
        "extensions.unifiedExtensions.enabled" = true;

        # Sidebar and top toolbar layout
        "zen.view.use-single-toolbar" = false;
      };

      userChrome = ''
        /* ── Hide individual extension icons, keep unified menu ─── */
        .unified-extensions-item {
          display: none !important;
        }

        /* ── Hide top new tab button ────────────────────────────── */
        #tabs-newtab-button {
          display: none !important;
        }

        /* ── Thin scrollbars ────────────────────────────────────── */
        :root {
          scrollbar-width: thin !important;
        }
      '';

      userContent = ''
        /* ── Prevent white flash on new tab / home ──────────────── */
        @-moz-document url("about:blank"), url("about:newtab"), url("about:home") {
          body {
            background-color: #${config.lib.stylix.colors.base00} !important;
          }
        }

        /* ── Prevent white flash on page load ───────────────────── */
        @-moz-document url-prefix() {
          :root {
            background-color: #${config.lib.stylix.colors.base00} !important;
          }
        }
      '';
    };
  };
}
