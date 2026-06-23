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
    cp -r ${src}/app.py ${src}/book.py ${src}/db.py ${src}/genres.py \
          ${src}/library.py ${src}/music.py ${src}/quality.py \
          ${src}/scanner.py ${src}/templates $out/
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/refinery              0750 refinery refinery -"
    "d /persist/refinery/covers       0750 refinery refinery -"
    "d /persist/refinery/spectrograms 0750 refinery refinery -"
    "d /persist/refinery/artists      0750 refinery refinery -"
    "d /persist/refinery/mb_artists   0750 refinery refinery -"
    "d /persist/refinery/book_covers  0750 refinery refinery -"
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
      REFINERY_WORKERS=3
      NAVIDROME_DB=/var/lib/navidrome/navidrome.db
      REFINERY_DOWNLOADS=/mnt/storage/downloads/slskd/complete
      REFINERY_MUSIC_TARGET=/mnt/storage/media/music
      REFINERY_BOOK_TARGET=/mnt/storage/media/books
      REFINERY_BOOK_COVER_DIR=/persist/refinery/book_covers
      LASTFM_API_KEY=${config.sops.placeholder."stats/lastfm_api_key"}
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
    after    = [ "mnt-storage.mount" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    # refinery needs write on:
    #  - /mnt/storage/media/music    (to create artist/album folders on approve)
    #  - /mnt/storage/downloads/slskd (to retag source files, then move them out)
    # The -d default ACL makes any new subfolder slskd creates inherit the
    # grant, so newly-downloaded albums are writable without re-running this.
    script = ''
      for dir in /mnt/storage/media/music /mnt/storage/media/books \
                 /mnt/storage/downloads/slskd; do
        if [ -d "$dir" ]; then
          ${pkgs.acl}/bin/setfacl -R -m u:refinery:rwx "$dir" || true
          ${pkgs.acl}/bin/setfacl -d -R -m u:refinery:rwx "$dir" || true
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
      Environment      = [
        "PATH=${pkgs.flac}/bin:${pkgs.ffmpeg-headless}/bin:${pkgs.sox}/bin:${pkgs.rsgain}/bin:${pkgs.calibre}/bin"
      ];
      ExecStart        = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart          = "on-failure";
      RestartSec       = "5s";
    };
  };
}
