{ pkgs, ... }:

let
  imageDir = "/persist/var/lib/libvirt/images";
  virsh = "${pkgs.libvirt}/bin/virsh -c qemu:///system";
in
{
  systemd.services.zealos-setup = {
    description = "Download ZealOS ISO and define VM";
    after = [ "network-online.target" "libvirtd.service" ];
    wants = [ "network-online.target" "libvirtd.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail
      ISO="${imageDir}/ZealOS.iso"
      if [ ! -f "$ISO" ]; then
        mkdir -p ${imageDir}
        ZEALOS_URL=$(${pkgs.curl}/bin/curl -sf \
          https://api.github.com/repos/Zeal-Operating-System/ZealOS/releases/latest \
          | ${pkgs.python3}/bin/python3 -c \
          "import sys,json; a=json.load(sys.stdin)['assets']; print(next(x['browser_download_url'] for x in a if x['name'].endswith('.iso')))")
        ${pkgs.curl}/bin/curl -L --progress-bar "$ZEALOS_URL" -o "$ISO"
      fi
      ${virsh} dominfo ZealOS >/dev/null 2>&1 && ${virsh} undefine --managed-save ZealOS || true
      ${virsh} define /dev/stdin << XMLEOF
      <domain type='kvm'>
        <name>ZealOS</name>
        <memory unit='KiB'>524288</memory>
        <vcpu>2</vcpu>
        <os>
          <type arch='x86_64' machine='q35'>hvm</type>
          <boot dev='cdrom'/>
        </os>
        <devices>
          <controller type='sata' index='0'>
            <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
          </controller>
          <disk type='file' device='cdrom'>
            <driver name='qemu' type='raw'/>
            <source file='${imageDir}/ZealOS.iso'/>
            <target dev='sda' bus='sata'/>
            <readonly/>
          </disk>
          <graphics type='spice' autoport='yes'/>
          <video><model type='vga'/></video>
        </devices>
      </domain>
      XMLEOF
    '';
  };
}
