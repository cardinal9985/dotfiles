{ pkgs, ... }:

{
  security.rtkit.enable = true;

  # Realtime scheduling limits for the @audio group (Required by WineASIO)
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

    # Low-latency global defaults
    # 256/48000 (~5.3ms) is for Rocksmith on a Scarlett 2i2.
    # Rocksmith strictly requires 48000 Hz
    extraConfig.pipewire."92-low-latency" = {
      "context.properties" = {
        "default.clock.rate"        = 48000;
        "default.clock.quantum"     = 256;
        "default.clock.min-quantum" = 64;
        "default.clock.max-quantum" = 512;
      };
    };

    # Match latency for PulseAudio clients (Steam uses the Pulse sink)
    extraConfig.pipewire-pulse."92-low-latency" = {
      "pulse.properties" = {
        "pulse.min.req"     = "256/48000";
        "pulse.default.req" = "256/48000";
        "pulse.max.req"     = "512/48000";
      };
    };
  };

  # Focusrite Scarlett 2i2 3rd Gen (USB ID 1235:8210)
  # Allows the @audio group to access ALSA mixer controls without sudo,
  # which is required for alsa-scarlett-gui to function correctly.
  #
  # NOTE: Before alsa-scarlett-gui shows full controls, you must disable MSD
  # mode on the interface once. Hold the 48V button while plugging in USB
  # the interface will reboot into audio-only mode. This persists across reboots
  # and only needs to be done once.
  services.udev.extraRules = ''
    SUBSYSTEM=="sound", ACTION=="add", \
      ATTRS{idVendor}=="1235", ATTRS{idProduct}=="8210", \
      GROUP="audio", MODE="0660"
  '';

  # Prevent USB autosuspend, a common cause of dropouts with USB audio interfaces.
  # threadirqs moves hardware IRQ handling off the main audio thread,
  # reducing xruns caused by GPU/NVMe interrupt storms on Wayland.
  boot.kernelParams = [
    "usbcore.autosuspend=-1"
    "threadirqs"
  ];

  environment.systemPackages = with pkgs; [
    # Focusrite Scarlett hardware mixer GUI
    # Controls input level (Inst vs Line), Air mode, phantom power, and direct monitor.
    # Set Input 1 to "Inst" mode for guitar, and turn Direct Monitor OFF while
    # playing Rocksmith (the game handles its own monitoring through the ASIO chain).
    alsa-scarlett-gui

    # PipeWire patchbay, verify JACK port connections during first setup
    qpwgraph

    # Audio device profile switcher, set Scarlett to "Pro Audio" profile
    # for exclusive hardware access and minimum latency
    pavucontrol
  ];
}
