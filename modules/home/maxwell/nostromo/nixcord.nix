{ ... }:

{
  programs.nixcord = {
    enable = true;
    discord.equicord.enable = true;
    discord.vencord.enable = false;

    quickCss = ''
      body {
        --font: 'JetBrainsMono Nerd Font';
        --code-font: 'JetBrainsMono Nerd Font';
        font-weight: 400;

        --gap: 12px;
        --divider-thickness: 4px;
        --border-thickness: 1px;
        --animations: on;
        --list-item-transition: 0.2s ease;
        --dms-icon-transition: 0.2s ease;
        --corner-text: 'nostromo';
        --panel-button-hover-transition: 0.2s ease;
        --sidebar-hover-transition: 0.2s ease;
        --chatbar-height: 47px;
        --small-user-panel: on;
        --transparency-tweaks: off;
        --remove-bg-layer: off;
        --panel-blur: off;
        --custom-dms-background: off;
        --background-image-url: url("");

        /* Everforest Dark Hard colors */
        --bg-1: #1e2326;
        --bg-2: #2b3339;
        --bg-3: #323c41;
        --bg-4: #3d484d;
        --hover: hsl(200, 12%, 25%);
        --active: hsl(200, 12%, 28%);
        --selected: hsl(200, 12%, 28%);
        --accent-1: #a7c080;
        --accent-2: #83c092;
        --accent-3: #7fbbb3;
        --accent-4: #7fbbb3;
        --accent-5: #7a8478;
        --mention: hsla(97, 30%, 63%, 0.1);
        --mention-hover: hsla(97, 30%, 63%, 0.15);
        --text-1: #d3c6aa;
        --text-2: #9da9a0;
        --text-3: #859289;
        --text-4: #7a8478;
        --text-5: #4f585e;
        --icon-primary: #d3c6aa;
        --icon-secondary: #859289;
        --icon-subtle: #7a8478;
        --online-indicator: #a7c080;
        --dnd-indicator: #e67e80;
        --idle-indicator: #dbbc7f;
        --streaming-indicator: #d699b6;
        --white: #d3c6aa;
        --black: #1e2326;
      }
    '';

    config = {
      useQuickCss = true;
      themeLinks = [
        "https://refact0r.github.io/midnight-discord/build/midnight.css"
      ];

      frameless = false;
      disableMinSize = true;
      plugins = {
        anonymiseFileNames = {
          enable = true;
          anonymiseByDefault = true;
          method = 0;
          randomisedLength = 7;
          spoilerMessages = false;
        };
        callTimer = {
          enable = true;
          allCallTimers = true;
          format = "stopwatch";
          showRoleColor = true;
          showSeconds = true;
          showWithoutHover = true;
          trackSelf = true;
          watchLargeGuilds = false;
        };
        crashHandler = {
          enable = true;
          attemptToNavigateToHome = true;
          attemptToPreventCrashes = true;
        };
        equibopStreamFixes = {
          enable = true;
          bitsPerPixelPct = 8;
          keyframeInterval = 5000;
          minBitrate = 500;
          preventDownscale = true;
          preventFramerateReduction = true;
          raiseBitrateCaps = true;
          removeResolutionCap = true;
          unlockQualityOptions = true;
        };
        equicordHelper = {
          enable = true;
          accountStandingButton = true;
          disableAdoptTagPrompt = true;
          forceRoleIcon = true;
          noBulletPoints = false;
          noMirroredCamera = false;
          noModalAnimation = true;
          refreshSlashCommands = true;
          removeActivitySection = false;
          restoreFileDownloadButton = true;
          showYourOwnActivityButtons = true;
        };
        equicordToolbox = {
          enable = true;
          showPluginMenu = false;
        };
        fakeNitro = {
          enable = true;
          enableEmojiBypass = true;
          enableStickerBypass = true;
          enableStreamQualityBypass = false;
          disableEmbedPermissionCheck = true;
          emojiSize = 48.0;
          hyperLinkText = "{{NAME}}";
          stickerSize = 160.0;
          transformCompoundSentence = true;
          transformEmojis = true;
          transformStickers = true;
          useEmojiHyperLinks = true;
          useStickerHyperLinks = true;
        };
        fixImagesQuality = {
          enable = true;
          originalImagesInChat = false;
        };
        gitHubRepos = {
          enable = true;
          showStars = true;
          showLanguage = true;
        };
        ircColors = {
          enable = true;
          applyColorOnlyInDms = false;
          applyColorOnlyToUsersWithoutColor = true;
          lightness = 70;
          memberListColors = true;
        };
        messageLogger = {
          enable = true;
          collapseDeleted = false;
          deleteStyle = "text";
          ignoreBots = true;
          ignoreSelf = false;
          ignoreSelfEdits = false;
          inlineEdits = true;
          logDeletes = true;
          logEdits = true;
          separatedDiffs = false;
          showEditDiffs = false;
        };
        messageLoggerEnhanced = {
          enable = true;
          alwaysLogCurrentChannel = true;
          alwaysLogDirectMessages = true;
          attachmentFileExtensions = "png,jpg,jpeg,gif,webp,mp4,webm,mp3,ogg,wav,mpv";
          cacheLimit = 1000;
          cacheMessagesFromServers = false;
          hideMessageFromMessageLoggers = true;
          hideMessageFromMessageLoggersDeletedMessage = "redacted";
          ignoreBots = true;
          ignoreMutedCategories = true;
          ignoreMutedChannels = true;
          ignoreMutedGuilds = true;
          ignoreSelf = false;
          ignoreWebhooks = true;
          messageLimit = 500;
          messagesToDisplayAtOnceInLogs = 100;
          permanentlyRemoveLogByDefault = false;
          preserveCurrentChannel = true;
          saveImages = true;
          saveMessages = true;
          showLogsButton = true;
          showWhereMessageIsFrom = false;
          sortNewest = true;
          timeBasedCleanupMinutes = 0;
        };
        newGuildSettings = {
          enable = true;
          events = true;
          everyone = true;
          guild = true;
          highlights = true;
          messages = 1;
          mobilePush = true;
          role = true;
          showAllChannels = true;
          voiceChannels = false;
        };
        platformIndicators = {
          enable = true;
          colorMobileIndicator = true;
          consoleIcon = "equicord";
          list = true;
          messages = true;
          profiles = true;
          showBots = false;
        };
        questify = {
          enable = true;
          autoCompleteQuestsSimultaneously = false;
          completeVideoQuestsQuicker = true;
          disableAccountPanelPromo = true;
          makeMobileVideoQuestsDesktopCompatible = true;
        };
        relationshipNotifier = {
          enable = true;
          friendRequestCancels = true;
          friends = true;
          groups = true;
          notices = true;
          offlineRemovals = true;
          servers = true;
        };
        noNitroUpsell.enable = true;
        jumpTo.enable = true;
        guildPickerDumper.enable = true;
        gifPaste.enable = true;
        friendsSince.enable = true;
        fixCodeblockGap.enable = true;
        disableCallIdle.enable = true;
        disableDeepLinks.enable = true;
        plainFolderIcon.enable = true;
        readAllNotificationsButton.enable = true;
        volumeBooster.enable = true;
        clearUrls.enable = true;
        biggerStreamPreview.enable = true;
      };
    };
  };
}
