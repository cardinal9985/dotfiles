{ pkgs, ... }:

{
  services = {
    ratbagd.enable = true;
    hardware.openrgb.enable = true;
  };

  hardware = {
    i2c.enable = true;
    xpadneo.enable = true;
    uinput.enable = true;
  };

  environment.systemPackages = with pkgs; [
    piper
    openrgb-with-all-plugins
    input-remapper
    antimicrox
  ];
}
