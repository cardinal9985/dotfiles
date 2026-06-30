{ pkgs, ... }:

# SPT (Single Player Tarkov) + Fika launcher wrappers.
# Uses the native Linux SPT launcher (no Wine for the launcher itself), which
# lets PROTON_ENABLE_NVAPI be scoped only to EscapeFromTarkov.exe.
#
# Workflow for `tarkov`:
#   1. Native launcher opens - log in (auto-login should work)
#   2. Click "Copy Launch Arguments"
#   3. Game launches automatically with NVAPI + Smooth Motion
#
# Produces three commands + matching .desktop entries:
#   tarkov         - main game launcher (native launcher -> EFT via Proton)
#   tarkov-svm     - SVM Server Value Modifier GUI (Greed.exe)
#   tarkov-server  - local SPT.Server.Linux for offline testing (no Pelican)

let
  sptRoot   = "/home/maxwell/games/lutris/escape-from-tarkov";
  sptInner  = "${sptRoot}/spt";
  sptSubdir = "${sptInner}/SPT";

  protonEnv = ''
    unset LD_PRELOAD
    export PROTONPATH=${pkgs.proton-ge-bin.steamcompattool}
    export WINEPREFIX=${sptRoot}
    export GAMEID=umu-default
    export PROTON_VERB=waitforexitandrun
  '';

  # Native Linux SPT launcher - runs without Wine so NVAPI never touches it.
  # Files live in the Nix store (read-only), but the launcher's LogManager tries
  # to create user/ next to the binary. We sync to ~/.local/share at runtime so
  # AppContext.BaseDirectory resolves to a writable path.
  sptLauncherLinuxFiles = pkgs.stdenv.mkDerivation {
    pname = "spt-launcher-linux";
    version = "4.0.13";
    src = pkgs.fetchurl {
      url = "https://github.com/ThunderArtist/spt-launcher-linux/releases/download/4.0.13/SPT.Launcher.Linux-4.0.13.tar.gz";
      hash = "sha256-1nVB7vMJNkyUWnGL3LDhoL/1X6oqS4so9vzSz3cJNlo=";
    };
    dontBuild = true;
    installPhase = ''
      mkdir -p $out/share
      cp -r SPT.Launcher.Linux/. $out/share/
      chmod +x $out/share/SPT.Launcher.Linux
    '';
  };

  sptLauncherLinux = pkgs.writeShellScriptBin "spt-launcher-linux" ''
    RUNTIME_DIR="$HOME/.local/share/spt-launcher-linux"
    mkdir -p "$RUNTIME_DIR"
    ${pkgs.rsync}/bin/rsync -a --delete --exclude='user' --chmod=Du+rwx,Fu+rw \
      "${sptLauncherLinuxFiles}/share/" "$RUNTIME_DIR/"
    export DOTNET_ROOT="${pkgs.dotnet-aspnetcore_9}/share/dotnet"
    exec ${pkgs.steam-run}/bin/steam-run "$RUNTIME_DIR/SPT.Launcher.Linux" "$@"
  '';

  tarkov = pkgs.writeShellScriptBin "tarkov" ''
    set -euo pipefail

    ARGS_FILE=$(mktemp /tmp/eft-launch-args.XXXXX)
    LAUNCHER_PID=""

    cleanup() {
      [ -n "$LAUNCHER_PID" ] && kill "$LAUNCHER_PID" 2>/dev/null || true
      rm -f "$ARGS_FILE"
    }
    trap cleanup EXIT

    # Open native launcher in background
    ${sptLauncherLinux}/bin/spt-launcher-linux &
    LAUNCHER_PID=$!

    echo "SPT Launcher open - log in and click 'Copy Launch Arguments' to start the game"

    # Poll clipboard until EFT token appears or launcher exits
    while kill -0 "$LAUNCHER_PID" 2>/dev/null; do
      CLIP=$(${pkgs.wl-clipboard}/bin/wl-paste 2>/dev/null || true)
      if printf '%s' "$CLIP" | ${pkgs.gnugrep}/bin/grep -q -- '-token='; then
        printf '%s' "$CLIP" > "$ARGS_FILE"
        break
      fi
      sleep 0.5
    done

    if [ ! -s "$ARGS_FILE" ]; then
      echo "No launch arguments captured. Click 'Copy Launch Arguments' before closing the launcher." >&2
      exit 1
    fi

    kill "$LAUNCHER_PID" 2>/dev/null || true
    LAUNCHER_PID=""

    LAUNCH_ARGS=$(cat "$ARGS_FILE")
    # Strip leading exe name if launcher copies "EscapeFromTarkov.exe -token=..."
    LAUNCH_ARGS=$(printf '%s' "$LAUNCH_ARGS" | ${pkgs.gnused}/bin/sed 's|[^ ]*EscapeFromTarkov\.exe ||')

    ${protonEnv}
    export PROTON_ENABLE_NVAPI=1
    export NVPRESENT_ENABLE_SMOOTH_MOTION=1
    export DXVK_ASYNC=1
    # winhttp=n,b: forces Wine to load the local winhttp.dll (BepInEx doorstop)
    # so mods including Fika hook into Unity correctly.
    export WINEDLLOVERRIDES="winhttp=n,b"

    cd ${sptInner}
    eval "exec ${pkgs.gamemode}/bin/gamemoderun ${pkgs.umu-launcher}/bin/umu-run EscapeFromTarkov.exe $LAUNCH_ARGS"
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

  # Local SPT.Server.Linux runner. Useful for offline play / testing without
  # touching the Pelican-hosted server. Conflicts with Pelican if both run at
  # the same time (port 6969 collision).
  tarkov-server = pkgs.writeShellScriptBin "tarkov-server" ''
    set -euo pipefail
    unset LD_PRELOAD
    export DOTNET_ROOT=${pkgs.dotnet-aspnetcore_9}/share/dotnet
    cd ${sptSubdir}
    exec ${pkgs.steam-run}/bin/steam-run ./SPT.Server.Linux "$@"
  '';
in
{
  home.packages = [
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
}
