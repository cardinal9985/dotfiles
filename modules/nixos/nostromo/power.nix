{ ... }:

{
  systemd.targets = {
    sleep.enable = false;
    suspend.enable = false;
    hibernate.enable = false;
    hybrid-sleep.enable = false;
  };

  services.logind.settings.Login = {
    HandleLidSwitch = "ignore";
    HandleSuspendKey = "ignore";
    HandleHibernateKey = "ignore";
    IdleAction = "ignore";
  };

  powerManagement = {
    enable = true;
    cpuFreqGovernor = "performance";
  };

  # KDE's power-profiles-daemon overrides amd-pstate-epp with "balanced" EPP hints
  # at login, undoing cpuFreqGovernor=performance. Disable it - PPD is for laptops
  # with battery/dock switching, not a fixed-power workstation.
  services.power-profiles-daemon.enable = false;

}
