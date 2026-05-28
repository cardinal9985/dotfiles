{ ... }:

{
  programs.nixcord = {
    enable = true;
    discord.equicord.enable = true;
    discord.vencord.enable = false;

    config = {
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
        disableCameras.enable = true;
        disableDeepLinks.enable = true;
        plainFolderIcon.enable = true;
        readAllNotificationsButton.enable = true;
        volumeBooster.enable = true;
        ClearURLs.enable = true;
        biggerStreamPreview.enable = true;
      };
    };
  };
}
