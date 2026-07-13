{ pkgs, inputs, ... }:

let

  #   tarkov         - SPT.Launcher.exe via Proton (no NVAPI - avoids WPF dropdown crash)
  #   tarkov-svm     - SVM Server Value Modifier GUI (Greed.exe)
  #   tarkov-server  - local SPT.Server.Linux for offline testing (no Pelican)

  sptRoot   = "/home/maxwell/games/escape-from-tarkov";
  sptInner  = "${sptRoot}/spt";
  sptSubdir = "${sptInner}/SPT";

  protonEnv = ''
    unset LD_PRELOAD
    export PROTONPATH=${pkgs.proton-ge-bin.steamcompattool}
    export WINEPREFIX=${sptRoot}
    export GAMEID=umu-default
    export PROTON_VERB=waitforexitandrun
  '';

  tarkov = pkgs.writeShellScriptBin "tarkov" ''
    set -euo pipefail
    ${protonEnv}
    export DXVK_ASYNC=1
    # winhttp=n,b: forces Wine to load the local winhttp.dll (BepInEx doorstop)
    # so mods including Fika hook into Unity correctly.
    export WINEDLLOVERRIDES="winhttp=n,b"
    cd ${sptSubdir}
    ${pkgs.umu-launcher}/bin/umu-run 'X:\games\escape-from-tarkov\spt\SPT\SPT.Launcher.exe'
  '';

  tarkov-svm = pkgs.writeShellScriptBin "tarkov-svm" ''
    set -euo pipefail
    ${protonEnv}
    GREED='${sptSubdir}/user/mods/[SVM] Server Value Modifier/Greed.exe'
    if [ ! -f "$GREED" ]; then
      echo "Greed.exe not found at $GREED" >&2
      exit 1
    fi
    # Greed.exe expects cwd to be the SPT install root (next to
    # EscapeFromTarkov.exe). It uses a relative path
    # "SPT/user/mods/[SVM] Server Value Modifier/" to locate its DLL.
    cd ${sptInner}
    exec ${pkgs.umu-launcher}/bin/umu-run "$GREED" "$@"
  '';

  tarkov-server = pkgs.writeShellScriptBin "tarkov-server" ''
    set -euo pipefail
    unset LD_PRELOAD
    export DOTNET_ROOT=${pkgs.dotnet-aspnetcore_9}/share/dotnet
    cd ${sptSubdir}
    exec ${pkgs.steam-run}/bin/steam-run ./SPT.Server.Linux "$@"
  '';
in
{
  home.packages = with pkgs; [
    mangohud
    heroic
    lutris
    winetricks
    protontricks
    umu-launcher
    steamcmd
    vintagestory
    rimsort
    ckan
    doomrunner
    uzdoom
    #inputs.nix-citizen.packages.${pkgs.stdenv.hostPlatform.system}.rsi-launcher

    (pkgs.prismlauncher.override {
      additionalPrograms = [
        ffmpeg
        zenity
      ];
      gamemodeSupport = true;
      jdks = [
        zulu8
        zulu17
        zulu21
      ];
    })

    tarkov
    tarkov-svm
    tarkov-server
  ];

  xdg.desktopEntries = {
    tarkov = {
      name        = "SPT Tarkov";
      genericName = "Single Player Tarkov + Fika";
      comment     = "Patched EFT through Proton with all mods";
      exec        = "${tarkov}/bin/tarkov";
      icon        = "applications-games";
      type        = "Application";
      categories  = [ "Game" ];
      terminal    = false;
    };

    tarkov-svm = {
      name       = "SPT - SVM Config (Greed)";
      comment    = "Server Value Modifier preset editor";
      exec       = "${tarkov-svm}/bin/tarkov-svm";
      icon       = "preferences-system";
      type       = "Application";
      categories = [ "Game" "Settings" ];
      terminal   = false;
    };
  };

  # Rocksmith 2014 declarative audio wiring via rocksmith-nix
  # This generates RS_ASIO.ini + Rocksmith.ini and exports the rocksmith-launch
  # wrapper script that must be set as the Steam launch option:
  #
  #   rocksmith-launch %command%
  #
  # Optional: gamemoderun rocksmith-launch %command%
  #           MANGOHUD=1 gamemoderun rocksmith-launch %command%
  #
  # The wrapper auto-deploys all DLLs into the Proton prefix on every launch.
  myModules.home.rocksmith = {
    enable = true;

    # latencyBuffer: 1-4, lower = less latency. Start at 2, drop to 1 if stable.
    latencyBuffer = 2;

    # Must match default.clock.quantum / default.clock.rate in audio.nix
    pipewireLatency = "256/48000";
  };
}
