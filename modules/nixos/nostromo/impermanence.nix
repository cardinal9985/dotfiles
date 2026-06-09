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
      {
        directory = "/var/lib/ollama";
        user = "ollama";
        group = "ollama";
        mode = "0755";
      }
      {
        directory = "/var/lib/open-webui";
        user = "open-webui";
        group = "open-webui";
        mode = "0755";
      }
    ];
    files = [
      "/etc/machine-id"
      "/etc/ssh/ssh_host_ed25519_key"
      "/etc/ssh/ssh_host_rsa_key"
    ];
  };
}
