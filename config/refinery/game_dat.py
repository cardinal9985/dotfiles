"""No-Intro + Redump DAT cache.

DAT files list every known-good ROM/disc dump with size + CRC32 + MD5 +
SHA1 + canonical name. Parsing on every import would be silly - one SNES
DAT alone is ~20k entries. We parse once into a SQLite index keyed on each
hash and look up O(1) on import.

Source: libretro-database mirrors the no-intro and redump DATs in
ClrMamePro format under metadat/{no-intro,redump}/. Auto-refreshes weekly
via the refinery-dat-refresh systemd timer."""

import logging
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

import requests

import game_platforms as plats

log = logging.getLogger("refinery.dat")

DAT_DIR  = os.environ.get("REFINERY_DAT_DIR", "/persist/refinery/dats")
DAT_DB   = os.environ.get("REFINERY_DAT_DB",  "/persist/refinery/dats.db")
UA       = "ishimura-refinery/1.0 (https://refinery.ishimura.lol)"

LIBRETRO_RAW = "https://raw.githubusercontent.com/libretro/libretro-database/master"


def _url(folder, filename):
    return f"{LIBRETRO_RAW}/metadat/{folder}/{quote(filename)}"


# platform_slug -> (url, kind). kind = "nointro" or "redump", informational
# only (parser is shared).
DAT_SOURCES = {
    # No-Intro: cartridge / handheld
    "nes":    (_url("no-intro", "Nintendo - Nintendo Entertainment System.dat"),      "nointro"),
    "snes":   (_url("no-intro", "Nintendo - Super Nintendo Entertainment System.dat"), "nointro"),
    "n64":    (_url("no-intro", "Nintendo - Nintendo 64.dat"),                        "nointro"),
    "gb":     (_url("no-intro", "Nintendo - Game Boy.dat"),                           "nointro"),
    "gbc":    (_url("no-intro", "Nintendo - Game Boy Color.dat"),                     "nointro"),
    "gba":    (_url("no-intro", "Nintendo - Game Boy Advance.dat"),                   "nointro"),
    "nds":    (_url("no-intro", "Nintendo - Nintendo DS.dat"),                        "nointro"),
    "vb":     (_url("no-intro", "Nintendo - Virtual Boy.dat"),                        "nointro"),
    "md":     (_url("no-intro", "Sega - Mega Drive - Genesis.dat"),                   "nointro"),
    "sms":    (_url("no-intro", "Sega - Master System - Mark III.dat"),               "nointro"),
    "gg":     (_url("no-intro", "Sega - Game Gear.dat"),                              "nointro"),
    "32x":    (_url("no-intro", "Sega - 32X.dat"),                                    "nointro"),
    "pce":    (_url("no-intro", "NEC - PC Engine - TurboGrafx 16.dat"),               "nointro"),
    "2600":   (_url("no-intro", "Atari - 2600.dat"),                                  "nointro"),
    "5200":   (_url("no-intro", "Atari - 5200.dat"),                                  "nointro"),
    "7800":   (_url("no-intro", "Atari - 7800.dat"),                                  "nointro"),
    "lynx":   (_url("no-intro", "Atari - Lynx.dat"),                                  "nointro"),
    "jaguar": (_url("no-intro", "Atari - Jaguar.dat"),                                "nointro"),
    "ngp":    (_url("no-intro", "SNK - Neo Geo Pocket.dat"),                          "nointro"),
    "ws":     (_url("no-intro", "Bandai - WonderSwan.dat"),                           "nointro"),
    # Redump: disc-based
    "ps1":    (_url("redump",   "Sony - PlayStation.dat"),                            "redump"),
    "ps2":    (_url("redump",   "Sony - PlayStation 2.dat"),                          "redump"),
    "psp":    (_url("redump",   "Sony - PlayStation Portable.dat"),                   "redump"),
    "saturn": (_url("redump",   "Sega - Saturn.dat"),                                 "redump"),
    "dc":     (_url("redump",   "Sega - Dreamcast.dat"),                              "redump"),
    "scd":    (_url("redump",   "Sega - Mega-CD - Sega CD.dat"),                      "redump"),
    "pcecd":  (_url("redump",   "NEC - PC Engine CD - TurboGrafx-CD.dat"),            "redump"),
    "3do":    (_url("redump",   "The 3DO Company - 3DO.dat"),                         "redump"),
    "gc":     (_url("redump",   "Nintendo - GameCube.dat"),                           "redump"),
    "wii":    (_url("redump",   "Nintendo - Wii.dat"),                                "redump"),
    "xbox":   (_url("redump",   "Microsoft - Xbox.dat"),                              "redump"),
    "x360":   (_url("redump",   "Microsoft - Xbox 360.dat"),                          "redump"),
}


def _db():
    conn = sqlite3.connect(DAT_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the table once. Idempotent."""
    Path(DAT_DB).parent.mkdir(parents=True, exist_ok=True)
    with _db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                platform   TEXT NOT NULL,
                name       TEXT NOT NULL,
                size       INTEGER,
                crc32      TEXT,
                md5        TEXT,
                sha1       TEXT,
                kind       TEXT,
                PRIMARY KEY (platform, name)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_crc32 ON entries(crc32)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_md5   ON entries(md5)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sha1  ON entries(sha1)")


_GAME_NAME_RE = re.compile(r'^\s*name\s+"([^"]+)"', re.MULTILINE)
_ROM_LINE_RE  = re.compile(
    r'\brom\s*\(\s*name\s+"([^"]+)"'
    r'\s+size\s+(\d+)'
    r'(?:\s+crc\s+(\S+))?'
    r'(?:\s+md5\s+(\S+))?'
    r'(?:\s+sha1\s+(\S+))?'
    r'\s*\)',
    re.IGNORECASE,
)


def _split_game_blocks(text):
    """Yield the inner text of each top-level `game ( ... )` block.
    ClrMamePro is paren-nested but only one level for our needs - rom (...)
    lines are on a single line so we don't need full balanced-paren parsing.
    We just split on `^game (` and stop each chunk at the next one (or EOF)."""
    blocks = re.split(r'(?m)^\s*game\s*\(\s*$', text)
    # blocks[0] is the header (clrmamepro block), skip it
    for chunk in blocks[1:]:
        # Trim at the closing ')' that terminates this game block - it's the
        # first line that is just ')' with optional whitespace.
        end = re.search(r'(?m)^\s*\)\s*$', chunk)
        yield chunk[:end.start()] if end else chunk


def _parse_dat(path, platform, kind):
    """Yield (name, size, crc32, md5, sha1) for every rom entry in a
    ClrMamePro DAT. One game block may contain multiple rom entries
    (e.g. Sega CD discs with audio tracks)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        log.warning("DAT read failed %s: %s", path, e)
        return

    for block in _split_game_blocks(text):
        name_m = _GAME_NAME_RE.search(block)
        if not name_m:
            continue
        name = name_m.group(1)
        for rom_m in _ROM_LINE_RE.finditer(block):
            _rom_name, size, crc32, md5, sha1 = rom_m.groups()
            try:
                size = int(size) if size else None
            except (TypeError, ValueError):
                size = None
            yield (name,
                   size,
                   (crc32 or "").lower(),
                   (md5   or "").lower(),
                   (sha1  or "").lower())


def refresh_one(platform, url, kind):
    """Download one DAT and load it into the hash index. Replaces existing
    entries for that platform."""
    os.makedirs(DAT_DIR, exist_ok=True)
    out = os.path.join(DAT_DIR, f"{platform}.dat")
    log.info("dat: fetch %s -> %s", url, out)
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": UA})
        r.raise_for_status()
        with open(out, "wb") as f:
            f.write(r.content)
    except Exception as e:
        log.warning("dat fetch failed %s: %s", url, e)
        return 0

    n = 0
    with _db() as c:
        c.execute("DELETE FROM entries WHERE platform = ?", (platform,))
        for name, size, crc32, md5, sha1 in _parse_dat(out, platform, kind):
            c.execute(
                "INSERT OR REPLACE INTO entries "
                "(platform, name, size, crc32, md5, sha1, kind) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (platform, name, size, crc32, md5, sha1, kind),
            )
            n += 1
    log.info("dat: %s -> %d entries", platform, n)
    return n


def refresh_all():
    """Refresh every DAT we have a source for. Called by the systemd timer
    and on demand from the UI."""
    init_db()
    total = 0
    for platform, (url, kind) in DAT_SOURCES.items():
        total += refresh_one(platform, url, kind)
    log.info("dat: refresh complete (%d total entries across %d platforms)",
             total, len(DAT_SOURCES))
    return total


def lookup_by_hash(crc32=None, md5=None, sha1=None, platform=None):
    """Find a DAT entry by any of the three hashes. Returns dict or None.
    Caller should provide whichever hash they have - usually CRC32 (fastest
    to compute) is enough for cartridge ROMs, MD5/SHA1 for disc images."""
    where, params = [], []
    if crc32:
        where.append("crc32 = ?")
        params.append(crc32.lower())
    if md5:
        where.append("md5   = ?")
        params.append(md5.lower())
    if sha1:
        where.append("sha1  = ?")
        params.append(sha1.lower())
    if not where:
        return None
    if platform:
        where.append("platform = ?")
        params.append(platform)
    sql = ("SELECT * FROM entries WHERE " + " AND ".join(where) +
           " LIMIT 1")
    with _db() as c:
        row = c.execute(sql, params).fetchone()
    return dict(row) if row else None


# Region detection from canonical name. No-Intro / Redump use a fairly
# standard set of region tags inside parens. We score by user preference.
REGION_TAG = re.compile(r"\(([^)]+)\)")
REGION_NORMALIZE = {
    "usa":            "USA", "us": "USA", "u": "USA",
    "europe":         "EUR", "eur": "EUR", "e": "EUR",
    "japan":          "JPN", "jp": "JPN", "j": "JPN",
    "world":          "WLD", "w": "WLD",
    "australia":      "AUS", "korea": "KOR",
    "china":          "CHN", "asia": "ASI", "brazil": "BRA",
    "spain":          "ESP", "france": "FRA", "germany": "DEU",
    "italy":          "ITA", "uk":     "UK",
}


def region_of(name):
    """Pull the first recognised region code from a no-intro/redump name."""
    for tag in REGION_TAG.findall(name or ""):
        for piece in re.split(r"[,;]", tag):
            key = piece.strip().lower()
            if key in REGION_NORMALIZE:
                return REGION_NORMALIZE[key]
    return None
