{ ... }:

{
  boot.loader = {
    grub = {
      enable = true;
      efiSupport = false;
    };
    timeout = 5;
  };
}
