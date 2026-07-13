{ pkgs, ... }:

{
  # Stub loader so dynamically-linked ELF binaries built for generic Linux
  # (Proton wine, VSCode server, downloaded release tarballs, etc.) can find
  # a working libc + friends without needing steam-run wrappers everywhere.
  programs.nix-ld.enable = true;
  programs.nix-ld.libraries = with pkgs; [
    stdenv.cc.cc
    zlib
    fuse3
    icu
    zstd
    openssl
    curl
    expat
    xz
  ];
}
