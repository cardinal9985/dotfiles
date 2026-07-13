{ ... }:

{
  services.gammastep = {
    enable = true;
    dawnTime = "7:00-8:00";
    duskTime = "20:00-21:00";
    temperature = {
      day = 6500;
      night = 3500;
    };
  };
}
