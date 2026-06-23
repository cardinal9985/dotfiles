{ config, pkgs, ... }:

let
  src = ../../../config/refinery;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    apscheduler
    requests
    mutagen
    numpy
  ]);

  app = pkgs.runCommand "ishimura-refinery" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/db.py ${src}/genres.py ${src}/music.py \
          ${src}/quality.py ${src}/scanner.py ${src}/templates $out/
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/refinery        0750 refinery refinery -"
    "d /persist/refinery/covers 0750 refinery refinery -"
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
    extraGroups  = [ "users" ];
  };
  users.groups.refinery = {};

  sops.templates."refinery.env" = {
    owner   = "refinery";
    content = ''
      REFINERY_DB_PATH=/persist/refinery/refinery.db
      REFINERY_COVER_DIR=/persist/refinery/covers
      REFINERY_DOWNLOADS=/mnt/storage/downloads/slskd/complete
      REFINERY_MUSIC_TARGET=/mnt/storage/media/music
      LASTFM_API_KEY=${config.sops.placeholder."stats/lastfm_api_key"}
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
      # flac + ffmpeg-headless are called as subprocesses by quality.py for
      # integrity verification and spectral analysis.
      Environment      = [
        "PATH=${pkgs.flac}/bin:${pkgs.ffmpeg-headless}/bin"
      ];
      ExecStart        = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart          = "on-failure";
      RestartSec       = "5s";
    };
  };
}
