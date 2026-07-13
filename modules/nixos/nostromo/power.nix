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

  services.power-profiles-daemon.enable = false;

}
