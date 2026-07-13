{ pkgs, ... }:

{
  home.packages = with pkgs; [
    tenacity                 # Audio Editing
    reaper                   # DAW
    reaper-sws-extension     # Reaper Plugin
    reaper-reapack-extension # Reaper Package Manager
    yabridge                 # VST Bridge
    synthesia                # Rocksmith but for a piano
    odin2                    # Odin 2 Synthesizer Plugin
  ];
}
