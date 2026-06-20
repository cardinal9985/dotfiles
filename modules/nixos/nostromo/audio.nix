{ pkgs, ... }:

{
  security.rtkit.enable = true;

  security.pam.loginLimits = [
    { domain = "@audio"; item = "memlock"; type = "-"; value = "unlimited"; }
    { domain = "@audio"; item = "rtprio";  type = "-"; value = "99"; }
  ];

  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    jack.enable = true;
    wireplumber.enable = true;

    extraConfig.pipewire."92-low-latency" = {
      "context.properties" = {
        "default.clock.rate"        = 48000;
        "default.clock.quantum"     = 256;
        "default.clock.min-quantum" = 64;
        "default.clock.max-quantum" = 512;
      };
    };

    extraConfig.pipewire-pulse."92-low-latency" = {
      "pulse.properties" = {
        "pulse.min.req"     = "256/48000";
        "pulse.default.req" = "256/48000";
        "pulse.max.req"     = "512/48000";
      };
    };
  };

  # NOTE: Before alsa-scarlett-gui shows full controls, you must disable MSD
  # mode on the interface once. Hold the 48V button while plugging in USB
  # the interface will reboot into audio-only mode. This persists across reboots
  # and only needs to be done once.
  services.udev.extraRules = ''
    SUBSYSTEM=="sound", ACTION=="add", \
      ATTRS{idVendor}=="1235", ATTRS{idProduct}=="8210", \
      GROUP="audio", MODE="0660"
  '';

  boot.kernelParams = [
    "usbcore.autosuspend=-1"
    "threadirqs"
  ];

  environment.systemPackages = with pkgs; [
    alsa-scarlett-gui
    qpwgraph
    pavucontrol
  ];
}
