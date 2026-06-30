{ pkgs, ... }:

let
  hwSink  = "alsa_output.pci-0000_11_00.6.analog-stereo";
  # EasyEffects owns the PipeWire default sink, so wpctl @DEFAULT_AUDIO_SINK@
  # targets the virtual EasyEffects node (which EasyEffects ignores for volume).
  # We look up the real hardware sink ID at runtime instead.
  hwSinkId = ''$(${pkgs.pipewire}/bin/pw-dump | ${pkgs.jq}/bin/jq -r '[.[] | select(.info.props["node.name"] == "${hwSink}")][0].id')'';

  volUp = pkgs.writeShellScriptBin "vol-up" ''
    ${pkgs.wireplumber}/bin/wpctl set-volume -l 1.5 ${hwSinkId} 5%+
  '';

  volDown = pkgs.writeShellScriptBin "vol-down" ''
    ${pkgs.wireplumber}/bin/wpctl set-volume ${hwSinkId} 5%-
  '';

  volMute = pkgs.writeShellScriptBin "vol-mute" ''
    ${pkgs.wireplumber}/bin/wpctl set-mute ${hwSinkId} toggle
  '';
in
{
  home.packages = with pkgs; [
    easyeffects
    volUp
    volDown
    volMute
  ];

  services.easyeffects = {
    enable = true;
    preset = "music";
  };

  xdg.dataFile."easyeffects/output/music.json".source  = ../../../../config/easyeffects/music.json;
  xdg.dataFile."easyeffects/output/gaming.json".source = ../../../../config/easyeffects/gaming.json;
  xdg.dataFile."easyeffects/output/movies.json".source = ../../../../config/easyeffects/movies.json;
  xdg.dataFile."easyeffects/output/flat.json".source   = ../../../../config/easyeffects/flat.json;
  xdg.dataFile."easyeffects/output/night.json".source  = ../../../../config/easyeffects/night.json;
  xdg.dataFile."easyeffects/output/voice.json".source  = ../../../../config/easyeffects/voice.json;
}
