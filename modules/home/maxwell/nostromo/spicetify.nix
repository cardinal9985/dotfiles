{ pkgs, config, inputs, ... }:

let
  spicePkgs = inputs.spicetify-nix.legacyPackages.${pkgs.system};
  s = config.lib.stylix.colors;
in
{
  stylix.targets.spicetify.enable = false;

  programs.spicetify = {
    enable = true;
    theme = spicePkgs.themes.bloom;

    customColorScheme = {
      text               = s.base05; # main text
      subtext            = s.base04; # secondary text
      sidebar-text       = s.base05;
      main               = s.base00; # main background
      sidebar            = s.base01; # sidebar background
      player             = s.base00;
      card               = s.base01;
      shadow             = s.base00;
      selected-row       = s.base02;
      button             = s.base0D; # accent (blue)
      button-active      = s.base0D;
      button-disabled    = s.base03;
      tab-active         = s.base0D;
      notification       = s.base0B; # green
      notification-error = s.base08; # red
      misc               = s.base03;
    };

    enabledExtensions = with spicePkgs.extensions; [
      loopyLoop
      shuffle
      history
      betterGenres
      adblock
    ];
  };
}
