{ pkgs, ... }:

# SPT (Single Player Tarkov) + Fika launcher wrappers.
# Wraps SPT.Launcher.exe in umu-run + Proton-GE with the WINEDLLOVERRIDES
# that BepInEx needs (winhttp=n,b) so doorstop hooks into Unity correctly.
#
# Produces three commands + matching .desktop entries:
#   tarkov         - main game launcher (Proton + Fika)
#   tarkov-svm     - SVM Server Value Modifier GUI (Greed.exe)
#   tarkov-server  - local SPT.Server.Linux for offline testing (no Pelican)

let
  sptRoot   = "/home/maxwell/games/lutris/escape-from-tarkov";
  sptInner  = "${sptRoot}/spt";
  sptSubdir = "${sptInner}/SPT";

  # Shared Proton env. Hardcoding nostromo's wine-prefix path because there
  # is exactly one SPT install on this machine; if it ever moves, change
  # sptRoot above.
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
    # winhttp=n,b: force wine to load the local winhttp.dll (BepInEx doorstop)
    # instead of wine's built-in. Without it BepInEx never hooks into Unity
    # and SPT mods (incl. Fika) don't load.
    export WINEDLLOVERRIDES="winhttp=n,b"
    cd ${sptSubdir}
    exec ${pkgs.umu-launcher}/bin/umu-run ${sptSubdir}/SPT.Launcher.exe "$@"
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
