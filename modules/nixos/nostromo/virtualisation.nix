{ pkgs, ... }:
{
  virtualisation.libvirtd = {
    enable = true;
    qemu = {
      package = pkgs.qemu_kvm;
      runAsRoot = false;
      swtpm.enable = true;
      vhostUserPackages = [ pkgs.virtiofsd ];
    };
  };

  boot.kernelModules = [ "nbd" "vhost_net" "vhost_vsock" ];

  programs.virt-manager.enable = true;

  services.spice-vdagentd.enable = true;

  users.users.maxwell.extraGroups = [ "libvirtd" "kvm" ];

  networking.firewall.trustedInterfaces = [ "virbr0" "virbr1" ];

  environment.systemPackages = with pkgs; [
    virt-manager
    virt-viewer
    x11docker
    libguestfs
    spice-gtk
  ];
}
