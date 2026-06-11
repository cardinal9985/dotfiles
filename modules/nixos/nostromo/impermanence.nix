{ ... }:
{
  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
      "/etc/nixos"
      "/etc/NetworkManager/system-connections"
      "/var/lib/bluetooth"
      "/var/lib/systemd/coredump"
      "/var/lib/nixos"
      "/var/lib/libvirt"
      "/var/lib/tailscale"
    ];
    files = [
      "/etc/machine-id"
      "/etc/ssh/ssh_host_ed25519_key"
      "/etc/ssh/ssh_host_rsa_key"
    ];
  };
}
