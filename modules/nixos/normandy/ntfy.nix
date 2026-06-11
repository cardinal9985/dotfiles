{ ... }:

{
  services.ntfy-sh = {
    enable = true;
    settings = {
      base-url = "http://normandy:8080";
      listen-http = ":8080";
      cache-file = "/var/cache/ntfy/cache.db";
      cache-duration = "12h";
      attachment-cache-dir = "/var/cache/ntfy/attachments";
      behind-proxy = false;
      auth-default-access = "read-write";
    };
  };

  systemd.tmpfiles.rules = [
    "d /var/cache/ntfy             0750 ntfy-sh ntfy-sh -"
    "d /var/cache/ntfy/attachments 0750 ntfy-sh ntfy-sh -"
  ];
}
