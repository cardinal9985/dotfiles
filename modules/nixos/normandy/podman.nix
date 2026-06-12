{ ... }:

{
  networking.firewall.extraForwardRules = ''
    iifname "podman*" accept comment "podman containers -> outbound"
    oifname "podman*" ct state established,related accept comment "outbound replies -> podman containers"
  '';

  virtualisation = {
    podman = {
      enable = true;
      dockerCompat = true;
      defaultNetwork.settings.dns_enabled = true;
      autoPrune = {
        enable = true;
        dates = "weekly";
        flags = [ "--all" ];
      };
    };
    oci-containers.backend = "podman";
  };
}
