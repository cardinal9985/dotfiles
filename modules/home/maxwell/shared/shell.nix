{ ... }:

{
  # nix-index-database provides a pre-built weekly-updated index of all files
  # in nixpkgs. The hmModules.nix-index module (wired in via flake.nix
  # sharedModules) handles the database itself and the command-not-found handler.

  # comma: `, <binary>` runs any nixpkgs binary ephemerally without installing.
  # Enabled here as a module option rather than a standalone package.
  programs.nix-index-database.comma.enable = true;

  programs.zsh = {
    enable = true;
    autocd = true;

    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;
    historySubstringSearch.enable = true;

    history = {
      size = 10000;
      save = 10000;
      ignoreDups = true;
      ignoreSpace = true;
      share = true;
    };
  };

  programs.zoxide = {
    enable = true;
    enableZshIntegration = true;
  };

  programs.fzf = {
    enable = true;
    enableZshIntegration = true;
    defaultOptions = [ "--preview 'bat --color=always --style=numbers {}'" ];
  };

  programs.bat = {
    enable = true;
    config = {
      style = "numbers,changes,header";
    };
  };

  programs.starship = {
    enable = true;
    enableZshIntegration = true;
  };
}
