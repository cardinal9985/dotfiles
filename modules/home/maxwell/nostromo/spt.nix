{ pkgs, ... }:

# SPT (Single Player Tarkov) + Fika launcher wrappers.
# Wraps SPT.Launcher.exe in umu-run + Proton-GE with the WINEDLLOVERRIDES
# that BepInEx needs (winhttp=n,b) so doorstop hooks into Unity correctly.
#
# Produces three commands + matching .desktop entries:
#   spt-launcher    - main game launcher (Proton + Fika)
#   spt-svm-config  - SVM Server Value Modifier GUI (Greed.exe)
#   spt-server      - local SPT.Server.Linux for offline testing (no Pelican)

let
  sptRoot   = "/home/maxwell/games/lutris/escape-from-tarkov";
  sptInner  = "${sptRoot}/spt";
  sptSubdir = "${sptInner}/SPT";

  # Shared Proton env. Hardcoding nostromo's wine-prefix path because there
  # is exactly one SPT install on this machine; if it ever moves, change
  # sptRoot above.
  protonEnv = ''
    unset LD_PRELOAD
    export PROTONPATH=${pkgs.proton-ge-bin}
    export WINEPREFIX=${sptRoot}
    export GAMEID=umu-default
    export PROTON_VERB=waitforexitandrun
  '';

  spt-launcher = pkgs.writeShellScriptBin "spt-launcher" ''
    set -euo pipefail
    ${protonEnv}
    # winhttp=n,b: force wine to load the local winhttp.dll (BepInEx doorstop)
    # instead of wine's built-in. Without it BepInEx never hooks into Unity
    # and SPT mods (incl. Fika) don't load.
    export WINEDLLOVERRIDES="winhttp=n,b"
    cd ${sptSubdir}
    exec ${pkgs.umu-launcher}/bin/umu-run ${sptSubdir}/SPT.Launcher.exe "$@"
  '';

  spt-svm-config = pkgs.writeShellScriptBin "spt-svm-config" ''
    set -euo pipefail
    ${protonEnv}
    GREED='${sptSubdir}/user/mods/[SVM] Server Value Modifier/Greed.exe'
    if [ ! -f "$GREED" ]; then
      echo "Greed.exe not found at $GREED" >&2
      exit 1
    fi
    cd "$(dirname "$GREED")"
    exec ${pkgs.umu-launcher}/bin/umu-run "$GREED" "$@"
  '';

  # Local SPT.Server.Linux runner. Useful for offline play / testing without
  # touching the Pelican-hosted server. Conflicts with Pelican if both run at
  # the same time (port 6969 collision).
  spt-server = pkgs.writeShellScriptBin "spt-server" ''
    set -euo pipefail
    unset LD_PRELOAD
    export DOTNET_ROOT=${pkgs.dotnet-aspnetcore_9}/share/dotnet
    cd ${sptSubdir}
    exec ${pkgs.steam-run}/bin/steam-run ./SPT.Server.Linux "$@"
  '';
in
{
  home.packages = [
    spt-launcher
    spt-svm-config
    spt-server
  ];

  xdg.desktopEntries = {
    spt-launcher = {
      name        = "SPT Tarkov";
      genericName = "Single Player Tarkov + Fika";
      comment     = "Patched EFT through Proton with all mods";
      exec        = "${spt-launcher}/bin/spt-launcher";
      icon        = "applications-games";
      type        = "Application";
      categories  = [ "Game" ];
      terminal    = false;
    };

    spt-svm-config = {
      name       = "SPT - SVM Config (Greed)";
      comment    = "Server Value Modifier preset editor";
      exec       = "${spt-svm-config}/bin/spt-svm-config";
      icon       = "preferences-system";
      type       = "Application";
      categories = [ "Game" "Settings" ];
      terminal   = false;
    };
  };
}
