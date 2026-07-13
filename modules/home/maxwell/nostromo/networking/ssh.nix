{ ... }:

{
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;
    settings = {
      "*" = {
        ControlMaster = "auto";
        ControlPath = "~/.ssh/sockets/%r@%h-%p";
        ControlPersist = "10m";
        ServerAliveInterval = 60;
      };
      "ishimura" = {
        Hostname = "100.92.76.121";
        Port = 36475;
        User = "maxwell";
      };
      "normandy" = {
        Hostname = "100.108.98.70";
        Port = 36475;
        User = "maxwell";
      };
    };
  };

  home.file.".ssh/sockets/.keep".text = "";
}
