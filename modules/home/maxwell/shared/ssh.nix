{ ... }:

{
  programs.ssh = {
    enable = true;
    controlMaster = "auto";
    controlPath = "~/.ssh/sockets/%r@%h-%p";
    controlPersist = "10m";
    matchBlocks = {
      "ishimura" = {
        hostname = "100.92.76.121";
        port = 36475;
        user = "maxwell";
      };
      "normandy" = {
        hostname = "100.108.98.70";
        port = 36475;
        user = "maxwell";
      };
    };
  };

  home.file.".ssh/sockets/.keep".text = "";
}
