{ ... }:

{
  services.scrutiny = {
    enable = true;
    collector.enable = true;
    settings.web.database.location = "/persist/scrutiny/scrutiny.db";
    settings.web.listen.port = 47890;
  };

  services.smartd = {
    enable = true;
    devices = [
      { device = "/dev/sda"; }
      { device = "/dev/sdb"; }
    ];
  };

  systemd.tmpfiles.rules = [
    "d /persist/scrutiny 0755 root root -"
  ];
}
