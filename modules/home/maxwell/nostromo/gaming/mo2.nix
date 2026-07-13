{ pkgs, ... }:

let
  gamesRoot = "/home/maxwell/games";

  # Wrapper factory. Add another instance to home.packages by calling
  # mkMO2 { name = "skyrim"; ... } and referencing the result.
  mkMO2 =
    {
      name,
      mo2Dir,
      prefixDir,
    }:
    pkgs.writeShellScriptBin "mo2-${name}" ''
      set -euo pipefail
      export STEAM_COMPAT_DATA_PATH="${prefixDir}"
      export STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.steam/steam"
      mkdir -p "$STEAM_COMPAT_DATA_PATH" "${mo2Dir}"

      if [ ! -f "${mo2Dir}/ModOrganizer.exe" ]; then
        cat >&2 <<EOF
      MO2 not found at ${mo2Dir}/ModOrganizer.exe

      Download the portable MO2 archive (7z) from:
        https://github.com/ModOrganizer2/modorganizer/releases
      Extract into ${mo2Dir}/ so ${mo2Dir}/ModOrganizer.exe exists,
      then re-run mo2-${name}.
      EOF
        exit 1
      fi

      exec ${pkgs.umu-launcher}/bin/umu-run "${mo2Dir}/ModOrganizer.exe" "$@"
    '';

  mo2-anomaly = mkMO2 {
    name = "anomaly";
    mo2Dir = "${gamesRoot}/mo2/anomaly";
    prefixDir = "${gamesRoot}/prefixes/anomaly";
  };
in
{
  home.packages = [
    mo2-anomaly
  ];
}
