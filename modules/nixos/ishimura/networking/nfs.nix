{ ... }:

let
  tailnetCIDR = "100.64.0.0/10";
in
{
  services.nfs.server = {
    enable = true;
    exports = ''
      /mnt/storage  ${tailnetCIDR}(rw,sync,no_subtree_check,no_root_squash,fsid=0)
    '';
  };
}
