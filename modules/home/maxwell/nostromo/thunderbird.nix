{ config, ... }:

let
  inherit (config.lib.stylix) colors;
in

{
  programs.thunderbird = {
    enable = true;

    profiles.maxwell = {
      isDefault = true;

      settings = {
        # Privacy
        "mail.send_pluginsupported_mail" = false;
        "mailnews.headers.showUserAgent" = false;
        "mailnews.headers.showOrganization" = false;

        # Composition
        "mail.spellcheck.inline" = true;
        "mail.compose.autosave" = true;
        "mail.compose.autosaveinterval" = 5;

        # Reading
        "mail.openMessageBehavior" = 0;
        "mail.tabs.autoHide" = false;

        # Disable telemetry
        "toolkit.telemetry.enabled" = false;
        "datareporting.healthreport.uploadEnabled" = false;

        # Enable userChrome
        "toolkit.legacyUserProfileCustomizations.stylesheets" = true;
      };

      userChrome = ''
        /* ── Variables ─────────────────────────────────────────── */
        :root {
          --bg-0:   #${colors.base00};
          --bg-1:   #${colors.base01};
          --bg-2:   #${colors.base02};
          --bg-3:   #${colors.base03};
          --text-1: #${colors.base05};
          --text-2: #${colors.base04};
          --accent: #${colors.base0B};
          --border: #${colors.base02};

          --lwt-accent-color:                    var(--bg-0)   !important;
          --lwt-text-color:                      var(--text-1) !important;
          --toolbar-bgcolor:                     var(--bg-0)   !important;
          --toolbar-color:                       var(--text-1) !important;
          --toolbarbutton-hover-background:      var(--bg-2)   !important;
          --toolbarbutton-active-background:     var(--bg-3)   !important;
          --tabs-tabbar-background-color:        var(--bg-0)   !important;
          --tab-selected-bgcolor:                var(--bg-2)   !important;
          --tab-selected-textcolor:              var(--text-1) !important;
          --arrowpanel-background:               var(--bg-1)   !important;
          --arrowpanel-color:                    var(--text-1) !important;
          --arrowpanel-border-color:             var(--border) !important;
          --sidebar-background-color:            var(--bg-1)   !important;
          --sidebar-text-color:                  var(--text-1) !important;
          --sidebar-border-color:                var(--border) !important;
          --splitter-color:                      var(--border) !important;
        }

        /* ── Main window ────────────────────────────────────────── */
        #messengerWindow,
        #messenger,
        body {
          background-color: var(--bg-0) !important;
          color: var(--text-1) !important;
        }

        /* ── Toolbar ────────────────────────────────────────────── */
        #navigation-toolbox,
        #mail-toolbar-menubar2,
        #tabs-toolbar,
        #unifiedToolbar {
          background-color: var(--bg-0) !important;
          border-bottom: 1px solid var(--border) !important;
        }

        /* ── Folder pane ────────────────────────────────────────── */
        #folderPane,
        #folderTree,
        .sidebar-header {
          background-color: var(--bg-1) !important;
          color: var(--text-1) !important;
        }

        /* ── Message list ───────────────────────────────────────── */
        #threadTree,
        #threadPane {
          background-color: var(--bg-0) !important;
          color: var(--text-1) !important;
        }

        /* ── Message pane ───────────────────────────────────────── */
        #messagepanebox,
        #messagepane {
          background-color: var(--bg-0) !important;
        }

        /* ── Tabs ───────────────────────────────────────────────── */
        .tabmail-tab {
          background-color: var(--bg-1) !important;
          color: var(--text-2) !important;
        }

        .tabmail-tab[selected="true"] {
          background-color: var(--bg-2) !important;
          color: var(--text-1) !important;
        }

        /* ── Thin scrollbars ────────────────────────────────────── */
        :root {
          scrollbar-width: thin !important;
          scrollbar-color: var(--bg-3) var(--bg-0) !important;
        }
      '';
    };
  };
}
