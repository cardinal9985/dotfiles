{ pkgs, ... }:

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
        Cryptomining = true;
        Fingerprinting = true;
        Locked = true;
        Value = true;
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
        /* Hide horizontal tab bar */
        #TabsToolbar { visibility: collapse !important; }
      '';
    };
  };
}
