{ pkgs, ... }:

{
  home.packages = with pkgs; [

    # ─── [ CLI/TUI Tools ] ──────────────────────────────────────────────

    nvitop          # Nvidia Monitoring
    ncdu            # Disk Space Analyzer
    p7zip           # 7-Zip File Archiver
    lazygit         # TUI Git
    rsync           # File Copying
    superfile       # File Manager
    dooit           # Todo
    tldr            # Cheatsheets
    unar            # Archive Extracter
    unzip           # Archive Extracter
    openssl         # Encryption & Cryptography
    tree            # File/Directory Tree
    lazyjournal     # Log Viewer
    compose2nix     # Convert Docker Compose Files
    libnotify       # notify-send CLI for D-Bus notifications
    tailscale       # Zero-Trust Network Overlay
    android-tools   # ADB
    nfs-utils       # NFS Tools
    scrcpy          # Android Mirror and Control
    zstd            # File Compression Algorithm

    # ─── [ GUI Tools ] ──────────────────────────────────────────────────

    gparted                  # Partition Management
    flashprint               # 3D Printing
    kdePackages.kate         # Backup Text Editor
    kdePackages.dolphin      # Backup File Manager
    deskmat                  # Keybind Overlay

    # ─── [ Editors & Productivity ] ─────────────────────────────────────

    obsidian  # Notes and Journaling
    basalt    # TUI Obsidian Client

    # ─── [ Music & Audio ] ──────────────────────────────────────────────

    blanket    # Ambient Audio Generator
    tauon      # Offline Music Player
    puddletag  # Tag Editor
    wiremix    # TUI Audio Mixer

    # ─── [ Media & Entertainment ] ──────────────────────────────────────

    jellyfin-desktop  # Jellyfin Media Server Client
    freetube          # YouTube Client
    mpv               # Video Player

    # ─── [ Browsing ] ───────────────────────────────────────────────────

    tor-browser  # Private Browser

    # ─── [ Communication ] ──────────────────────────────────────────────

    discordchatexporter-desktop  # Export Discord Chats
    simplex-chat-desktop         # Private Messenger
    zuse                         # IRC Client

    # ─── [ Security ] ───────────────────────────────────────────────────

    ente-auth         # 2FA Authentication
    bitwarden-desktop # Password Manager
    rbw               # CLI Bitwarden
    proton-vpn        # VPN
    kdePackages.kleopatra # GPG Key Manager
    cakewallet        # Multi-Currency Crypto Wallet
    feather           # Monero Wallet

    # ─── [ Video Recording & Editing ] ──────────────────────────────────

    obs-studio            # Recording and Streaming
    obs-cmd               # CLI OBS
    kdePackages.kdenlive  # Video Editor
    handbrake             # Video Transcoding
    gpu-screen-recorder   # Hardware-accelerated screen recording / replay buffer

    # ─── [ Downloading ] ────────────────────────────────────────────────

    nicotine-plus  # Soulseek Client
    qbittorrent    # Torrent Client
    yt-dlp         # Youtube Downloader

    # ─── [ AI] ──────────────────────────────────────────────────────────

    claude-code     # Clanker

  ];
}
