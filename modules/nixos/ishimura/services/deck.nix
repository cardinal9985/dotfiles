{
  inputs,
  config,
  ...
}:

let
  hosts = import ../../shared/lib/hosts.nix;
  nostromoTailnetIP = hosts.nostromo.tailnet;
in
{
  imports = [ inputs.deck.nixosModules.default ];

  services.deck = {
    enable = true;
    environmentFile = config.sops.templates."deck.env".path;
    home = "/persist/deck";
    openFirewall = true;
    hangarStatusUrl = "http://${nostromoTailnetIP}:5010/public/status";

    services = [
      {
        name = "Jellyfin";
        description = "Media Server";
        url = "https://jellyfin.ishimura.lol";
        icon = "▶";
      }
      {
        name = "Navidrome";
        description = "Music Streaming";
        url = "https://music.ishimura.lol";
        icon = "♪";
      }
      {
        name = "BookLore";
        description = "Ebook Library";
        url = "https://books.ishimura.lol";
        icon = "❒";
      }
      {
        name = "ROMM";
        description = "Retro Games";
        url = "https://romm.ishimura.lol";
        icon = "▥";
      }
      {
        name = "Rec Room";
        description = "Chess, Poker, Blackjack";
        url = "https://rec.ishimura.lol";
        icon = "♞";
      }
      {
        name = "Tools";
        description = "Dev Utilities";
        url = "https://tools.ishimura.lol";
        icon = "⚙";
      }
      {
        name = "Requests";
        description = "Media Requests";
        url = "https://requests.ishimura.lol";
        icon = "✎";
      }
      {
        name = "Stats";
        description = "Your Stats";
        url = "https://stats.ishimura.lol";
        icon = "◍";
      }
      {
        name = "Search";
        description = "Meta-Search";
        url = "https://search.ishimura.lol";
        icon = "⌕";
      }
      {
        name = "News";
        description = "CEC Newspaper";
        url = "https://daily.ishimura.lol";
        icon = "☰";
      }
      {
        name = "SyncTube";
        description = "Watch Together";
        url = "https://watch.ishimura.lol";
        icon = "◑";
      }
      {
        name = "Moodist";
        description = "Ambient Sounds";
        url = "https://moodist.ishimura.lol";
        icon = "≋";
      }
      {
        name = "PrivateBin";
        description = "Encrypted Pastebin";
        url = "https://paste.ishimura.lol";
        icon = "✄";
      }
    ];

    games = [
      {
        name = "Vintage Story";
        slug = "vintage-story";
        description = "Wilderness survival sandbox in a ruined fantasy world";
        address = "games.ishimura.lol:42420";
        version = "1.22.3 (Stable)";
        icon = "▣";
        howTo = [
          "Open Vintage Story and log in with your account"
          "Click 'Multiplayer'"
          "Click 'Server connect'"
          "Paste 'games.ishimura.lol:42420' into the address field"
        ];
      }
      {
        name = "Killing Floor 2";
        slug = "killing-floor-2";
        description = "Wave-based co-op zed shooter. Bioticslab default, 6 slots";
        address = "games.ishimura.lol:7777";
        version = "1150";
        icon = "☣";
        howTo = [
          "Launch Killing Floor 2"
          "Press <b>~</b> (tilde) in-game to open the console"
          "Type <code>open games.ishimura.lol:7777</code> and hit Enter"
          "If prompted for a password, enter <b>Yw6vq8</b> If this fails just disconnect and connect again. It can be janky."
        ];
      }
      {
        name = "Escape from Tarkov: Fika";
        slug = "escape-from-tarkov-fika";
        description = "SPT (Single Player Tarkov) + Fika co-op";
        address = "https://games.ishimura.lol:6969";
        version = "SPT 4.0.13 / Fika 2.3.3";
        icon = "✪";
        howTo = [
          "Install Escape from Tarkov via the BSG launcher or other means"
          ''Download the <a href="/mods/tarkov/SPTInstaller.exe" target="_blank">SPT 4.0.13 installer</a> and install it pointing at your EFT directory''
          ''Download <a href="/mods/tarkov/mods.zip" target="_blank">mods.zip</a> and extract everything into your SPT install root''
          "Launch SPT.Launcher.exe (Wine/Proton on Linux, native on Windows)"
          "Go to settings in the top right of the SPT Launcher, turn on developer mode"
          "Change the url to 'https://games.ishimura.lol:6969'"
          "Create a profile with any name you want, pick an edition (I recommend unheard edition)"
          "In the EFT main menu, use the Fika panel to host or join a co-op session"
        ];
      }
    ];
  };

  systemd.tmpfiles.rules = [
    "d /persist/deck 0750 deck deck -"
  ];

  environment.persistence."/persist".directories = [
    {
      directory = "/persist/deck";
      user = "deck";
      group = "deck";
      mode = "0750";
    }
  ];

  sops.templates."deck.env" = {
    owner = "deck";
    content = ''
      SECRET_KEY=${config.sops.placeholder."deck/secret_key"}
    '';
  };
}
