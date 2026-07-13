{ inputs, ... }:

{
  imports = [ inputs.hangar.nixosModules.default ];

  services.hangar = {
    enable = true;
    port = 5010;
    home = "/persist/gameservers";
    managedUnits = [
      "kf2.service"
      "vintagestory.service"
      "tarkov-spt.service"
    ];
    openFirewall = true;
  };
}
