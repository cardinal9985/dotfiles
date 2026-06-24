"""No-Intro + Redump DAT cache.

DAT files (XML) list every known-good ROM/disc dump with size + CRC32 + MD5
+ SHA1 + canonical name. Parsing them on every import would be silly - one
SNES DAT alone is ~20k entries. So we parse once into a SQLite index keyed
on each hash, and look up O(1) on import.

DATs auto-refresh weekly via the refinery-dat-refresh systemd timer."""

import logging
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

import game_platforms as plats

log = logging.getLogger("refinery.dat")

DAT_DIR  = os.environ.get("REFINERY_DAT_DIR", "/persist/refinery/dats")
DAT_DB   = os.environ.get("REFINERY_DAT_DB",  "/persist/refinery/dats.db")
UA       = "ishimura-refinery/1.0 (https://refinery.ishimura.lol)"

# The no-intro/redump "datomatic" portals require login + per-set downloads
# (no rate-limit friendly bulk endpoint). The community-maintained mirrors
# below repackage the same files for unauthenticated fetch. If they break,
# switch to libretro's mirrors or upload your own DATs to /persist/dats/.
DAT_SOURCES = {
    # platform_slug -> (url, kind)
    # kind = "nointro" or "redump"; tells us how to interpret a few quirks
    # in the XML (e.g. redump uses one <game> per disc, no-intro one per ROM).
    "nes":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Nintendo%20Entertainment%20System.dat",      "nointro"),
    "snes":   ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Super%20Nintendo%20Entertainment%20System.dat", "nointro"),
    "n64":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Nintendo%2064.dat",                          "nointro"),
    "gb":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Game%20Boy.dat",                             "nointro"),
    "gbc":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Game%20Boy%20Color.dat",                     "nointro"),
    "gba":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Game%20Boy%20Advance.dat",                   "nointro"),
    "nds":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Nintendo%20DS.dat",                          "nointro"),
    "vb":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Virtual%20Boy.dat",                          "nointro"),
    "md":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%20Mega%20Drive%20-%20Genesis.dat",                  "nointro"),
    "sms":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%20Master%20System%20-%20Mark%20III.dat",            "nointro"),
    "gg":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%20Game%20Gear.dat",                                "nointro"),
    "32x":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%2032X.dat",                                        "nointro"),
    "pce":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/NEC%20-%20PC%20Engine%20-%20TurboGrafx%2016.dat",            "nointro"),
    "2600":   ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Atari%20-%202600.dat",                                      "nointro"),
    "5200":   ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Atari%20-%205200.dat",                                      "nointro"),
    "7800":   ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Atari%20-%207800.dat",                                      "nointro"),
    "lynx":   ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Atari%20-%20Lynx.dat",                                      "nointro"),
    "jaguar": ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Atari%20-%20Jaguar.dat",                                    "nointro"),
    "ngp":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/SNK%20-%20Neo%20Geo%20Pocket.dat",                          "nointro"),
    "ws":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Bandai%20-%20WonderSwan.dat",                               "nointro"),
    # Redump (disc-based) - libretro mirrors these too
    "ps1":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sony%20-%20PlayStation.dat",                                "redump"),
    "psp":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sony%20-%20PlayStation%20Portable.dat",                     "redump"),
    "saturn": ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%20Saturn.dat",                                     "redump"),
    "dc":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%20Dreamcast.dat",                                  "redump"),
    "scd":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Sega%20-%20Mega%20CD%20-%20Sega%20CD.dat",                  "redump"),
    "pcecd":  ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/NEC%20-%20PC%20Engine%20CD%20-%20TurboGrafx-CD.dat",        "redump"),
    "3do":    ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/The%203DO%20Company%20-%203DO.dat",                         "redump"),
    "gc":     ("https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20GameCube.dat",                               "redump"),
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


def _parse_dat(path, platform, kind):
    """Yield (name, size, crc32, md5, sha1) tuples from a DAT XML."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        log.warning("DAT parse failed %s: %s", path, e)
        return
    for game in tree.getroot().findall("game"):
        name = game.attrib.get("name") or ""
        for rom in game.findall("rom"):
            size  = rom.attrib.get("size")
            crc32 = (rom.attrib.get("crc")  or "").lower()
            md5   = (rom.attrib.get("md5")  or "").lower()
            sha1  = (rom.attrib.get("sha1") or "").lower()
            try:
                size = int(size) if size else None
            except (TypeError, ValueError):
                size = None
            yield name, size, crc32, md5, sha1


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
