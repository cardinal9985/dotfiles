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
    guessit
  ]);

  app = pkgs.runCommand "ishimura-refinery" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/bandcamp.py ${src}/book.py ${src}/db.py \
          ${src}/downloader.py ${src}/game_dat.py ${src}/game_igdb.py \
          ${src}/game_platforms.py ${src}/games.py ${src}/genres.py \
          ${src}/library.py ${src}/music.py ${src}/quality.py \
          ${src}/scanner.py ${src}/subtitles.py ${src}/targets.py \
          ${src}/video.py ${src}/templates $out/
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
    "d /persist/refinery/video_covers   0750 refinery refinery -"
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
      REFINERY_MOVIE_TARGET=/mnt/storage/media/movies
      REFINERY_SHOW_TARGET=/mnt/storage/media/shows
      REFINERY_ANIME_MOVIE_TARGET=/mnt/storage/media/anime/movies
      REFINERY_ANIME_SHOW_TARGET=/mnt/storage/media/anime/shows
      REFINERY_DOCUMENTARY_TARGET=/mnt/storage/media/documentaries
      REFINERY_DOCUSERIES_TARGET=/mnt/storage/media/docuseries
      REFINERY_SHORT_FILM_TARGET=/mnt/storage/media/short-films
      REFINERY_FAN_EDIT_FILM_TARGET=/mnt/storage/media/fan-edits
      REFINERY_VIDEO_COVER_DIR=/persist/refinery/video_covers
      REFINERY_SUBTITLE_LANGS=en
      TMDB_TOKEN=${config.sops.placeholder."requests/tmdb_token"}
      # OpenSubtitles: sign up at opensubtitles.com, grab an API key. To
      # enable, add `opensubtitles/{api_key,username,password}` to
      # secrets.yaml (sops edit), declare them in sops.nix, then swap the
      # empty lines below for placeholder references. Subtitle fetch is a
      # per-approve checkbox and silently no-ops when the key is unset.
      OPENSUBTITLES_API_KEY=
      OPENSUBTITLES_USERNAME=
      OPENSUBTITLES_PASSWORD=
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

  systemd.services.refinery-media-acl = {
    description = "Grant refinery user ACL write on music library + slskd inbox";
    wantedBy = [ "multi-user.target" ];
    after    = [ "mnt-storage.mount" "systemd-tmpfiles-setup.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };

    script = ''
      for dir in /mnt/storage/media/movies /mnt/storage/media/shows \
                 /mnt/storage/media/anime  /mnt/storage/media/anime/movies \
                 /mnt/storage/media/anime/shows \
                 /mnt/storage/media/documentaries \
                 /mnt/storage/media/docuseries \
                 /mnt/storage/media/short-films \
                 /mnt/storage/media/fan-edits; do
        mkdir -p "$dir" || true
      done
      for dir in /mnt/storage/media/music /mnt/storage/media/books \
                 /mnt/storage/media/roms  /mnt/storage/media/movies \
                 /mnt/storage/media/shows /mnt/storage/media/anime \
                 /mnt/storage/media/documentaries \
                 /mnt/storage/media/docuseries \
                 /mnt/storage/media/short-films \
                 /mnt/storage/media/fan-edits \
                 /mnt/storage/downloads/slskd; do
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
      Environment      = [
        "PATH=${pkgs.flac}/bin:${pkgs.ffmpeg-headless}/bin:${pkgs.sox}/bin:${pkgs.rsgain}/bin:${pkgs.calibre}/bin:${pkgs.yt-dlp}/bin:${pkgs.mame-tools}/bin:${pkgs.p7zip}/bin:${pkgs.unzip}/bin"
      ];
      ExecStart        = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart          = "on-failure";
      RestartSec       = "5s";
    };
  };

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
