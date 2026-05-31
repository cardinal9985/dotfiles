{ ... }:

{
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
