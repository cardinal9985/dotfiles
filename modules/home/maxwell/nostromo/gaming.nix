{ pkgs, inputs, ... }:

{
  home.packages = with pkgs; [
    mangohud
    heroic
    steamcmd
    vintagestory
    rimsort
    ckan
    doomrunner
    uzdoom
    inputs.nix-citizen.packages.${pkgs.stdenv.hostPlatform.system}.rsi-launcher

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
  ];

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

    # latencyBuffer: 1–4, lower = less latency. Start at 2; drop to 1 if stable.
    latencyBuffer = 2;

    # Must match default.clock.quantum / default.clock.rate in audio.nix
    pipewireLatency = "256/48000";
  };
}
