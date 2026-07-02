{ config, pkgs, ... }:

let
  src = ../../../config/refinery;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    apscheduler
    requests
    mutagen
    numpy
    ebooklib
  ]);

  app = pkgs.runCommand "ishimura-refinery" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/bandcamp.py ${src}/book.py ${src}/db.py \
          ${src}/downloader.py ${src}/game_dat.py ${src}/game_igdb.py \
          ${src}/game_platforms.py ${src}/games.py ${src}/genres.py \
          ${src}/library.py ${src}/music.py ${src}/quality.py \
          ${src}/scanner.py ${src}/targets.py ${src}/templates $out/
  '';

  reprocessLibrary = pkgs.writeShellScriptBin "refinery-reprocess-library"
    (builtins.readFile ../../../config/refinery/reprocess-library.sh);
in
{
  environment.systemPackages = [ reprocessLibrary ];

  systemd.tmpfiles.rules = [
    "d /persist/refinery              0750 refinery refinery -"
    "d /persist/refinery/covers       0750 refinery refinery -"
    "d /persist/refinery/spectrograms 0750 refinery refinery -"
    "d /persist/refinery/artists      0750 refinery refinery -"
    "d /persist/refinery/mb_artists     0750 refinery refinery -"
    "d /persist/refinery/mb_discography 0750 refinery refinery -"
    "d /persist/refinery/ol_authors     0750 refinery refinery -"
    "d /persist/refinery/ol_works       0750 refinery refinery -"
    "d /persist/refinery/book_covers    0750 refinery refinery -"
    "d /persist/refinery/game_covers    0750 refinery refinery -"
    "d /persist/refinery/dats           0750 refinery refinery -"
    "d /persist/refinery/backups        0750 refinery refinery -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/refinery"; user = "refinery"; group = "refinery"; mode = "0750"; }
  ];

  users.users.refinery = {
    isSystemUser = true;
    group        = "refinery";
    home         = "/var/lib/refinery";
    # Need to write into both the downloads area (to extract zips / move
    # processed items aside) and the media library (final destination).
    # `navidrome` group gives read on /var/lib/navidrome/navidrome.db so the
    # library view can list owned artists/albums (we already widened the WAL
    # files to group-write for the stats SQLite reader).
    # systemd-oom is the group on /mnt/storage/media (default ownership from
    # mergerfs creation - weird but real). Without it refinery can't create
    # artist folders in the music library on approve.
    extraGroups  = [ "users" "navidrome" "systemd-oom" ];
  };
  users.groups.refinery = {};

  sops.templates."refinery.env" = {
    owner   = "refinery";
    content = ''
      REFINERY_DB_PATH=/persist/refinery/refinery.db
      REFINERY_COVER_DIR=/persist/refinery/covers
      REFINERY_SPECTROGRAM_DIR=/persist/refinery/spectrograms
      REFINERY_ARTIST_PHOTO_DIR=/persist/refinery/artists
      REFINERY_MB_ARTIST_CACHE=/persist/refinery/mb_artists
      REFINERY_MB_DISCO_CACHE=/persist/refinery/mb_discography
      REFINERY_OL_AUTHOR_CACHE=/persist/refinery/ol_authors
      REFINERY_OL_WORKS_CACHE=/persist/refinery/ol_works
      REFINERY_WORKERS=3
      NAVIDROME_DB=/var/lib/navidrome/navidrome.db
      REFINERY_DOWNLOADS=/mnt/storage/downloads/slskd/complete
      REFINERY_MUSIC_TARGET=/mnt/storage/media/music
      REFINERY_BOOK_TARGET=/mnt/storage/media/books
      REFINERY_BOOK_COVER_DIR=/persist/refinery/book_covers
      REFINERY_GAME_TARGET=/mnt/storage/media/roms
      REFINERY_BIOS_TARGET=/mnt/storage/media/bios
      REFINERY_GAME_COVER_DIR=/persist/refinery/game_covers
      REFINERY_DAT_DIR=/persist/refinery/dats
      REFINERY_DAT_DB=/persist/refinery/dats.db
      LASTFM_API_KEY=${config.sops.placeholder."stats/lastfm_api_key"}
      IGDB_CLIENT_ID=${config.sops.placeholder."romm/igdb_client_id"}
      IGDB_CLIENT_SECRET=${config.sops.placeholder."romm/igdb_client_secret"}
      STEAMGRIDDB_API_KEY=${config.sops.placeholder."romm/steamgriddb_api_key"}
      RETROACHIEVEMENTS_API_KEY=${config.sops.placeholder."romm/retroachievements_api_key"}
      SCREENSCRAPER_USER=${config.sops.placeholder."romm/screenscraper_user"}
      SCREENSCRAPER_PASSWORD=${config.sops.placeholder."romm/screenscraper_password"}
      NTFY_URL=http://normandy:8080
      NTFY_TOPIC=ishimura-refinery
      NTFY_TOKEN=
    '';
  };

  # Grant the refinery user write access to the music library via ACL.
  # The dir is owned by maxwell:systemd-oom 0775, but mergerfs +
  # default_permissions doesn't reliably honor supplementary groups, so
  # adding refinery to systemd-oom alone isn't enough. ACL grants the user
  # specifically. The -d default ACL is inherited by any new artist/album
  # folders refinery creates. Re-applied on every activation so a backup
  # restore or stray chacl can't permanently break imports.
  systemd.services.refinery-media-acl = {
    description = "Grant refinery user ACL write on music library + slskd inbox";
    wantedBy = [ "multi-user.target" ];
    # Must run AFTER systemd-tmpfiles-setup. tmpfiles enforces mode 0755 on
    # /mnt/storage/downloads/slskd/{,complete,incomplete} which calls chmod
    # under the hood. chmod on a file with extended ACLs resets the ACL mask
    # to match the group bits (r-x), which silently downgrades refinery's
    # rwx grant to effective r-x. Setting m::rwx below is the explicit fix,
    # and the ordering makes sure we win the race.
    after    = [ "mnt-storage.mount" "systemd-tmpfiles-setup.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    # refinery needs write on:
    #  - /mnt/storage/media/music    (artist/album folders on approve)
    #  - /mnt/storage/media/books    (author folders on approve)
    #  - /mnt/storage/media/roms     (per-platform game folders, RomM shares these)
    #  - /mnt/storage/downloads/slskd (retag source files + accept uploads)
    # Default ACL on each root makes new subfolders inherit the grant, so
    # newly-created destinations are writable without re-running this. m::rwx
    # explicitly sets the mask so a subsequent chmod doesn't silently
    # downgrade refinery's effective access.
    script = ''
      for dir in /mnt/storage/media/music /mnt/storage/media/books \
                 /mnt/storage/media/roms  /mnt/storage/downloads/slskd; do
        if [ -d "$dir" ]; then
          ${pkgs.acl}/bin/setfacl -R    -m u:refinery:rwx,m::rwx "$dir" || true
          ${pkgs.acl}/bin/setfacl -d -R -m u:refinery:rwx,m::rwx "$dir" || true
        fi
      done
    '';
  };

  systemd.services.ishimura-refinery = {
    description = "USG Refinery - media intake, tagging, approval, and library import";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];
    serviceConfig = {
      Type             = "simple";
      User             = "refinery";
      Group            = "refinery";
      EnvironmentFile  = config.sops.templates."refinery.env".path;
      # External CLI subprocesses:
      #   flac/ffmpeg/sox/rsgain - music quality + spectrogram + replaygain
      #   calibre                - book format conversion (MOBI/AZW -> EPUB)
      #                            and cover/metadata embedding
      #   yt-dlp                 - URL downloader (bandcamp/youtube/etc) -> inbox
      #   chdman (mame-tools)    - ROM disc image conversion (BIN/CUE/ISO -> CHD)
      #   p7zip / unzip          - extract archived ROM downloads
      Environment      = [
        "PATH=${pkgs.flac}/bin:${pkgs.ffmpeg-headless}/bin:${pkgs.sox}/bin:${pkgs.rsgain}/bin:${pkgs.calibre}/bin:${pkgs.yt-dlp}/bin:${pkgs.mame-tools}/bin:${pkgs.p7zip}/bin:${pkgs.unzip}/bin"
      ];
      ExecStart        = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart          = "on-failure";
      RestartSec       = "5s";
    };
  };

  # Nightly SQLite snapshot. sqlite3 .backup is online-safe (doesn't lock
  # against running refinery). Keeps 14 days so an "oops I forgot all 171
  # albums I just approved" rollback is one cp away.
  systemd.services.refinery-db-backup = {
    description = "Nightly snapshot of refinery's SQLite DB";
    serviceConfig = {
      Type  = "oneshot";
      User  = "refinery";
      Group = "refinery";
    };
    script = ''
      set -euo pipefail
      DB=/persist/refinery/refinery.db
      OUT=/persist/refinery/backups
      [ -f "$DB" ] || exit 0
      STAMP=$(date +%Y-%m-%d)
      ${pkgs.sqlite}/bin/sqlite3 "$DB" ".backup '$OUT/$STAMP.db'"
      # Keep last 14 daily snapshots
      ls -1t "$OUT"/*.db 2>/dev/null | tail -n +15 | xargs -r rm -f
    '';
  };

  systemd.timers.refinery-db-backup = {
    description = "Trigger nightly refinery DB backup";
    wantedBy    = [ "timers.target" ];
    timerConfig = {
      OnCalendar         = "daily";
      Persistent         = true;        # catch-up after downtime
      RandomizedDelaySec = "30min";
    };
  };

  # Weekly DAT refresh - no-intro / redump release updates roughly weekly,
  # and a stale DAT just means new dumps aren't recognised until refresh.
  systemd.services.refinery-dat-refresh = {
    description = "Refresh no-intro / redump DAT files for ROM integrity";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    serviceConfig = {
      Type             = "oneshot";
      User             = "refinery";
      Group            = "refinery";
      EnvironmentFile  = config.sops.templates."refinery.env".path;
    };
    script = ''
      ${pythonEnv}/bin/python -c 'import sys; sys.path.insert(0, "${app}"); import game_dat; game_dat.refresh_all()'
    '';
  };

  systemd.timers.refinery-dat-refresh = {
    description = "Trigger weekly DAT refresh";
    wantedBy    = [ "timers.target" ];
    timerConfig = {
      OnCalendar         = "weekly";
      Persistent         = true;
      RandomizedDelaySec = "1h";
    };
  };
}
