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
      unset LD_PRELOAD
      export STEAM_COMPAT_DATA_PATH="${prefixDir}"
      export STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.steam/steam"
      export WINEPREFIX="${prefixDir}"
      export GAMEID=umu-default
      export PROTONPATH=${pkgs.proton-ge-bin.steamcompattool}
      export PROTON_VERB=waitforexitandrun
      # Force native Microsoft d3d DLLs; Wine's vkd3d-shader HLSL compiler
      # fails on some Anomaly shaders with "E5017: Reservation shader
      # target ps" not implemented. Native DLLs must be pre-installed in
      # the prefix (winetricks d3dcompiler_43/47 d3dx11_43 d3dx9_43).
      export WINEDLLOVERRIDES="d3dcompiler_43=n;d3dcompiler_47=n;d3dx11_43=n;d3dx9_43=n"
      # Xalia (Proton's accessibility bridge) crashes noisily on some Qt
      # apps including MO2; not required for anything we care about.
      export PROTON_DISABLE_XALIA=1
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

  # Patch a Wine user.reg to enable subpixel font smoothing (rgb).
  # Direct file edit — no wine invocation needed. Idempotent.
  mkFontsmoothTool =
    { name, prefixDir }:
    pkgs.writers.writePython3Bin "mo2-${name}-fontsmooth"
      {
        flakeIgnore = [
          "E501"
          "E203"
        ];
      }
      ''
        import re
        import sys
        from pathlib import Path

        REG = Path("${prefixDir}/pfx/user.reg")
        TARGET = r"[Control Panel\\Desktop]"
        DESIRED = {
            '"FontSmoothing"': '"2"',
            '"FontSmoothingType"': "dword:00000002",
            '"FontSmoothingGamma"': "dword:00000578",
            '"FontSmoothingOrientation"': "dword:00000001",
        }

        if not REG.is_file():
            print(f"error: {REG} not found. Run mo2-${name} first.", file=sys.stderr)
            sys.exit(1)

        lines = REG.read_text().splitlines(keepends=True)
        start = next((i for i, l in enumerate(lines) if l.startswith(TARGET)), None)

        if start is None:
            block = [f"{TARGET}\n"] + [f"{k}={v}\n" for k, v in DESIRED.items()] + ["\n"]
            REG.write_text("".join(lines) + "".join(block))
            print("added [Control Panel\\Desktop] section with fontsmoothing keys")
            sys.exit(0)

        end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("[")), len(lines))
        key_re = re.compile(r'^("[^"]+")=')
        seen = set()
        out = [lines[start]]
        for line in lines[start + 1 : end]:
            m = key_re.match(line)
            if m and m.group(1) in DESIRED:
                out.append(f"{m.group(1)}={DESIRED[m.group(1)]}\n")
                seen.add(m.group(1))
            else:
                out.append(line)
        for k, v in DESIRED.items():
            if k not in seen:
                out.append(f"{k}={v}\n")

        REG.write_text("".join(lines[:start] + out + lines[end:]))
        print("patched fontsmoothing keys in", REG)
      '';

  mo2-anomaly = mkMO2 {
    name = "anomaly";
    mo2Dir = "${gamesRoot}/mo2/anomaly";
    prefixDir = "${gamesRoot}/prefixes/anomaly";
  };

  mo2-anomaly-fontsmooth = mkFontsmoothTool {
    name = "anomaly";
    prefixDir = "${gamesRoot}/prefixes/anomaly";
  };
in
{
  home.packages = [
    mo2-anomaly
    mo2-anomaly-fontsmooth
  ];
}
