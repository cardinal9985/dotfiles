{ pkgs, ... }:

let
  simplefox = pkgs.fetchFromGitHub {
    owner = "migueravila";
    repo = "SimpleFox";
    rev = "master";
    sha256 = "sha256-iNILXnOZYbzy2/HcUpyiq6VOLA2C6fogAAwSWsTun1U=";
  };
in

{
  xdg.mimeApps = {
    defaultApplications = {
      "text/html" = "firefox.desktop";
      "x-scheme-handler/http" = "firefox.desktop";
      "x-scheme-handler/https" = "firefox.desktop";
      "x-scheme-handler/about" = "firefox.desktop";
      "x-scheme-handler/unknown" = "firefox.desktop";
    };
  };

  programs.firefox = {
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
        "extensions.activeThemeID" = "firefox-compact-dark@mozilla.org";

        # Sidebar
        "sidebar.revamp" = true;
        "sidebar.verticalTabs" = true;
        "sidebar.main.tools" = "bookmarks,history,syncedtabs";
        "sidebar.visibility" = "always-show";
      };

      userChrome = ''
        /* Hide native horizontal tab bar */
        #TabsToolbar { visibility: collapse !important; }

        /* Hide redundant sidebar header */
        #sidebar-header { display: none !important; }

        /* Everforest Dark Hard color overrides for SimpleFox */
        :root {
          --bg-1: #1e2326;
          --bg-2: #2b3339;
          --bg-3: #323c41;
          --bg-4: #3d484d;
          --hover: #3d484d;
          --active: #475258;
          --selected: #475258;
          --accent-1: #a7c080;
          --accent-2: #83c092;
          --accent-3: #7fbbb3;
          --accent-4: #d699b6;
          --accent-5: #7a8478;
          --mention: hsla(97, 30%, 63%, 0.1);
          --mention-hover: hsla(97, 30%, 63%, 0.15);
          --text-1: #d3c6aa;
          --text-2: #9da9a0;
          --text-3: #859289;
          --text-4: #7a8478;
          --text-5: #4f585e;
        }
      '' + builtins.readFile "${simplefox}/chrome/userChrome.css";

      userContent = builtins.readFile "${simplefox}/chrome/userContent.css";
    };
  };
}
