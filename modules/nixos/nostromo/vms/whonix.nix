{ pkgs, ... }:

let
  imageDir = "/persist/var/lib/libvirt/images";
  virsh = "${pkgs.libvirt}/bin/virsh -c qemu:///system";
  whonixVersion = "18.1.4.2";
  whonixUrl = "https://download.whonix.org/libvirt/${whonixVersion}/Whonix-LXQt-${whonixVersion}.Intel_AMD64.qcow2.libvirt.xz";
  whonixSigUrl = "${whonixUrl}.asc";
  whonixSigningKey = "https://www.whonix.org/keys/derivative.asc";
in
{
  systemd.services.whonix-setup = {
    description = "Download and import Whonix KVM images";
    after = [ "network-online.target" "libvirtd.service" ];
    wants = [ "network-online.target" "libvirtd.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail
      GATEWAY_IMG="${imageDir}/Whonix-Gateway.qcow2"
      WORKSTATION_IMG="${imageDir}/Whonix-Workstation.qcow2"
      if [ ! -f "$GATEWAY_IMG" ] || [ ! -f "$WORKSTATION_IMG" ]; then
        mkdir -p ${imageDir}
        TMP=$(mktemp -d)
        trap "rm -rf $TMP" EXIT

        ${pkgs.curl}/bin/curl -L --progress-bar "${whonixUrl}" -o "$TMP/whonix.libvirt.xz"
        ${pkgs.curl}/bin/curl -L --silent "${whonixSigUrl}" -o "$TMP/whonix.libvirt.xz.asc"
        ${pkgs.curl}/bin/curl -L --silent "${whonixSigningKey}" -o "$TMP/derivative.asc"

        GNUPGHOME=$(mktemp -d)
        export GNUPGHOME
        ${pkgs.gnupg}/bin/gpg --import "$TMP/derivative.asc"
        ${pkgs.gnupg}/bin/gpg --verify "$TMP/whonix.libvirt.xz.asc" "$TMP/whonix.libvirt.xz"

        ${pkgs.xz}/bin/xz -d "$TMP/whonix.libvirt.xz"
        ${pkgs.gnutar}/bin/tar -xf "$TMP/whonix.libvirt" -C "$TMP"

        ${pkgs.coreutils}/bin/cp --sparse=always "$TMP"/Whonix-Gateway*.qcow2 "$GATEWAY_IMG"
        ${pkgs.coreutils}/bin/cp --sparse=always "$TMP"/Whonix-Workstation*.qcow2 "$WORKSTATION_IMG"

        ${virsh} net-define "$TMP"/Whonix_external*.xml || true
        ${virsh} net-define "$TMP"/Whonix_internal*.xml || true
        ${virsh} net-autostart Whonix-External || true
        ${virsh} net-start Whonix-External || true
        ${virsh} net-autostart Whonix-Internal || true
        ${virsh} net-start Whonix-Internal || true
        ${virsh} define "$TMP"/Whonix-Gateway*.xml || true
        ${virsh} define "$TMP"/Whonix-Workstation*.xml || true
      fi


      ${virsh} setvcpus Whonix-Gateway 2 --config || true
      ${virsh} setmem Whonix-Gateway 1572864 --config || true
      ${virsh} set-user-password Whonix-Gateway root "" --encrypted || true

      ${virsh} setvcpus Whonix-Workstation 4 --config || true
      ${virsh} setmem Whonix-Workstation 6291456 --config || true
    '';
  };
}
