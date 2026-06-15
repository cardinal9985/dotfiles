{ ... }:

{
  imports = [
    ../shared/xdg.nix
    ../shared/shell.nix
    ../shared/git.nix
    ../shared/prompt.nix
    ./greet.nix
  ];
}
