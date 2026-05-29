final: prev: {
  deskmat = prev.python3Packages.buildPythonApplication {
    pname = "deskmat";
    version = "unstable-2025";

    src = prev.fetchFromGitHub {
      owner = "NicoSenerman";
      repo = "deskmat";
      rev = "main";
      sha256 = "sha256-SWBpkP/XrzXGilz6+6SnQ+TibccBxaMnnXmowH6b3cU=";
    };

    format = "other";

    nativeBuildInputs = [ prev.wrapGAppsHook4 ];

    propagatedBuildInputs = with prev; [
      gtk4
      gtk4-layer-shell
      python3Packages.pygobject3
      python3Packages.pyyaml
      tealdeer
    ];

    dontBuild = true;

    installPhase = ''
      mkdir -p $out/bin
      cp deskmat $out/bin/deskmat
      chmod +x $out/bin/deskmat
      substituteInPlace $out/bin/deskmat \
        --replace "python3" "${prev.python3}/bin/python3"
    '';
  };
}
