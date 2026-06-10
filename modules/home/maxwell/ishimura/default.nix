{ ... }:

{
  imports = [
    ../shared/shell.nix
    ../shared/git.nix
    ../shared/prompt.nix
    ./aliases.nix
    ./greet.nix
  ];
}
