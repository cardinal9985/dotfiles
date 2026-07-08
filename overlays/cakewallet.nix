final: prev:

let
  version = "6.2.1";
  bundleVersion = "6.2.0";
in
{
  cakewallet = prev.stdenv.mkDerivation {
    pname = "cakewallet";
    inherit version;

    src = prev.fetchurl {
      url = "https://github.com/cake-tech/cake_wallet/releases/download/v${version}/Cake_Wallet_v${bundleVersion}_Linux.tar.xz";
      sha256 = "116ak4a88ni5zfwmd8mkynqxc5kzcvsbrivfcgksgwnakc5h1xxg";
    };

    nativeBuildInputs = with prev; [
      autoPatchelfHook
      wrapGAppsHook3
      copyDesktopItems
    ];

    buildInputs = with prev; [
      gtk3
      glib
      pcre2
      libepoxy
      libsecret
      libGL
      lz4
      stdenv.cc.cc.lib
    ];

    dontBuild = true;
    dontConfigure = true;

    desktopItems = [
      (prev.makeDesktopItem {
        name = "cakewallet";
        desktopName = "Cake Wallet";
        comment = "Multi-currency crypto wallet";
        exec = "cakewallet";
        icon = "cakewallet";
        categories = [ "Office" "Finance" ];
        terminal = false;
      })
    ];

    installPhase = ''
      runHook preInstall

      mkdir -p $out/opt/cakewallet $out/bin
      cp -r . $out/opt/cakewallet/
      chmod +x $out/opt/cakewallet/cake_wallet

      makeWrapper $out/opt/cakewallet/cake_wallet $out/bin/cakewallet

      runHook postInstall
    '';
  };
}
