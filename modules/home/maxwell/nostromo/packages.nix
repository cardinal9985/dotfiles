{ pkgs, inputs, ... }:

{

  # Packages that should be installed to the user profile.
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

    # ─── [ Game Development ] ───────────────────────────────────────────

    godot-mono        # Game Engine
    blender           # 3D Modeling
    material-maker    # Procedural Materials Authoring
    libresprite       # Sprite Editor
    pixelorama        # Pixel Art

    # ─── [ Browsing ] ───────────────────────────────────────────────────

    tor-browser  # Private Browser
    brave        # Backup Browser

    # ─── [ Communication ] ──────────────────────────────────────────────

    discordchatexporter-desktop  # Export Discord Chats
    simplex-chat-desktop         # Private Messenger
    zuse                         # IRC Client

    # ─── [ Security ] ───────────────────────────────────────────────────

    ente-auth         # 2FA Authentication
    bitwarden-desktop # Password Manager
    rbw               # CLI Bitwarden
    proton-vpn        # VPN

    # ─── [ Audio Engineering ] ──────────────────────────────────────────

    tenacity                 # Audio Editing
    reaper                   # DAW
    reaper-sws-extension     # Reaper Plugin
    reaper-reapack-extension # Reaper Package Manager
    yabridge                 # VST Bridge
    synthesia                # Rocksmith but for a piano
    odin2                    # Odin 2 Synthesizer Plugin

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

    # ─── [ AI ] ─────────────────────────────────────────────────────────

    claude-code  # CLI Claude

    # ─── [ Hyprland ] ───────────────────────────────────────────────────

    grimblast       # Screenshot Tool
    grim            # Screenshot Backend
    slurp           # Region Selection
    swappy          # Screenshot Annotation
    cliphist        # Clipboard History
    wl-clipboard    # Wayland Clipboard
    playerctl       # Media Key Control
    pavucontrol     # Volume Mixer
    hyprpolkitagent # Authentication Agent

  ];

}
