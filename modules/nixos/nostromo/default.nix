{ ... }:

{

  imports = [
    # Modules
    ./network.nix
    ./nfs.nix
    ./tdarr-node.nix
    ./boot.nix
    ./gpu.nix
    ./audio.nix
    ./bluetooth.nix
    ./desktop.nix
    ./sops.nix
    ./stylix.nix
    ./substituters.nix
    ./user.nix
    ./packages.nix
    ./steam.nix
    ./swap.nix
    ./impermanence.nix
    ./security.nix
    ./power.nix
    ./peripherals.nix
    ./virtualisation.nix
    ./ssh.nix
    # VMs
    ./vms/zealos.nix
    ./vms/whonix.nix
  ];

}
