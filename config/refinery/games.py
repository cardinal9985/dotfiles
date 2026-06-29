"""Game ROM processor.

Phase 2 scope: classify a folder of downloaded files to a platform slug,
extract any disc-image archives so chdman can later convert their
contents, and stage one item per ROM file in the approval queue.

Hashing + DAT lookup + metadata enrichment + CHD conversion arrive in
later phases."""

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import zipfile
import zlib
from collections import Counter
from pathlib import Path

import db
import game_dat
import game_platforms as plats

log = logging.getLogger("refinery.games")

ARCHIVE_EXTS = {".zip", ".7z", ".rar"}

# Filename / folder-name hints used to disambiguate when multiple platforms
# share an extension (.iso, .bin, .cue, .zip). First match wins, so put
# more-specific patterns BEFORE more-general ones (PS2 before PS1, etc.).
PLATFORM_HINTS = [
    (r"\bplaystation\s*portable\b|\bpsp\b",            "psp"),
    (r"\bplaystation\s*2\b|\bps2\b",                   "ps2"),
    (r"\bplaystation\s*3\b|\bps3\b",                   "ps3"),
    (r"\bplaystation\b|\bpsx\b|\bps1\b|\bpsone\b",     "ps1"),
    (r"\bnintendo\s*64\b|\bn64\b",                     "n64"),
    (r"\bgamecube\b|\bngc\b|\bgcn\b",                  "gc"),
    (r"\bwii\s*u\b",                                   "wiiu"),
    (r"\bwii\b",                                       "wii"),
    (r"\bnew\s*nintendo\s*3ds\b|\b3ds\b",              "3ds"),
    (r"\bnintendo\s*ds\b|\bnds\b",                     "nds"),
    (r"\bgame\s*boy\s*advance\b|\bgba\b",              "gba"),
    (r"\bgame\s*boy\s*color\b|\bgbc\b",                "gbc"),
    (r"\bgame\s*boy\b|\bgb\b",                         "gb"),
    (r"\bsuper\s*nintendo\b|\bsnes\b|\bsfc\b",         "snes"),
    (r"\bnintendo\s*entertainment\s*system\b|\bnes\b|\bfamicom\b", "nes"),
    (r"\bvirtual\s*boy\b|\bvirtualboy\b",              "vb"),
    (r"\bswitch\b",                                    "switch"),
    (r"\bps\s*vita\b|\bvita\b",                        "vita"),
    (r"\bgenesis\b|\bmega\s*drive\b|\bmegadrive\b|\bmd\b", "md"),
    (r"\bsega\s*32x\b|\b32x\b",                        "32x"),
    (r"\bsega\s*cd\b|\bmega\s*cd\b|\bscd\b",           "scd"),
    (r"\bmaster\s*system\b|\bsms\b",                   "sms"),
    (r"\bgame\s*gear\b|\bgg\b",                        "gg"),
    (r"\bsaturn\b",                                    "saturn"),
    (r"\bdreamcast\b|\bdc\b",                          "dc"),
    (r"\bxbox\s*360\b|\bx360\b",                       "x360"),
    (r"\bxbox\b",                                      "xbox"),
    (r"\bpc\s*engine\s*cd\b|\btg\W*cd\b|\bturbo\s*grafx\s*cd\b|\bpcecd\b", "pcecd"),
    (r"\bpc\s*engine\b|\btg\W*16\b|\bturbo\s*grafx\b|\bpce\b",             "pce"),
    (r"\batari\s*2600\b|\b2600\b",                     "2600"),
    (r"\batari\s*5200\b|\b5200\b",                     "5200"),
    (r"\batari\s*7800\b|\b7800\b",                     "7800"),
    (r"\batari\s*lynx\b|\blynx\b",                     "lynx"),
    (r"\batari\s*jaguar\b|\bjaguar\b",                 "jaguar"),
    (r"\bneo\s*geo\s*pocket\b|\bngp\b",                "ngp"),
    (r"\bneo\s*geo\b|\bneogeo\b",                      "neogeo"),
    (r"\bwonderswan\b|\bws\b",                         "ws"),
    (r"\b3do\b",                                       "3do"),
    (r"\barcade\b|\bmame\b",                           "arcade"),
]

_HINT_RES = [(re.compile(p, re.IGNORECASE), slug) for p, slug in PLATFORM_HINTS]


def _hint_platform(text):
    if not text:
        return None
    for rx, slug in _HINT_RES:
        if rx.search(text):
            return slug
    return None


def _peek_archive(archive_path):
    """List filenames inside an archive without extracting. Empty list on
    failure - we never want a corrupt archive to block classification."""
    p   = Path(archive_path)
    ext = p.suffix.lower()
    try:
        if ext == ".zip":
            with zipfile.ZipFile(p) as zf:
                return [n for n in zf.namelist() if not n.endswith("/")]
        if ext == ".7z":
            r = subprocess.run(["7z", "l", "-ba", "-slt", str(p)],
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return []
            return [line.split("=", 1)[1].strip()
                    for line in r.stdout.splitlines()
                    if line.startswith("Path =")]
        if ext == ".rar":
            r = subprocess.run(["unrar", "lb", str(p)],
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return []
            return [n for n in r.stdout.splitlines() if n.strip()]
    except Exception as e:
        log.warning("archive peek failed %s: %s", p, e)
    return []


def classify(folder):
    """Determine the platform slug a folder of ROMs belongs to.

    Steps:
      1. Walk files. For each, collect candidate slugs from the extension
         (peeking into archives to use inner-file extensions).
      2. Tally votes per slug.
      3. If only one slug got votes, return it.
      4. Else use filename + folder-name hints (PS1, SNES, ...) to break
         the tie among the candidates that got votes.
      5. Else fall back to the highest-vote slug, alphabetical tiebreak."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return None

    votes        = Counter()
    file_records = []

    for f in folder_path.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        cands = set()

        if ext in ARCHIVE_EXTS:
            for inner in _peek_archive(f):
                iext = Path(inner).suffix.lower()
                cands.update(plats.for_extension(iext))
            # MAME ROMs ARE .zip, so include the archive ext too
            cands.update(plats.for_extension(ext))
        else:
            cands.update(plats.for_extension(ext))

        if cands:
            file_records.append((f, cands))
            for c in cands:
                votes[c] += 1

    if not votes:
        return None
    if len(votes) == 1:
        return next(iter(votes))

    # Look for a hint that picks among our candidates.
    hint = _hint_platform(folder_path.name)
    if hint and hint in votes:
        return hint
    for f, _ in file_records:
        h = _hint_platform(f.name)
        if h and h in votes:
            return h

    # No hint - take the most-voted, alphabetical tiebreak for determinism.
    top  = votes.most_common()
    best = top[0][1]
    return sorted(slug for slug, n in top if n == best)[0]


def list_rom_files(folder, platform):
    """Files that look like ROMs for `platform`. Bare files with a matching
    extension, plus archives whose contents include a matching extension."""
    p = Path(folder)
    if not p.is_dir():
        return []
    exts = set(plats.PLATFORMS[platform]["exts"])
    out  = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in exts:
            out.append(str(f))
            continue
        if ext in ARCHIVE_EXTS:
            for inner in _peek_archive(f):
                if Path(inner).suffix.lower() in exts:
                    out.append(str(f))
                    break
    return sorted(out)


def extract_disc_archives(folder, platform):
    """For disc-based platforms, extract any .zip/.7z/.rar in place so
    chdman can later see the BIN/CUE/ISO inside. Cartridge platforms keep
    archives wrapped (emulators read them directly)."""
    if not plats.PLATFORMS.get(platform, {}).get("disc_based"):
        return
    p = Path(folder)
    for f in list(p.rglob("*")):
        if not (f.is_file() and f.suffix.lower() in ARCHIVE_EXTS):
            continue
        out_dir = f.with_suffix("")
        out_dir.mkdir(exist_ok=True)
        log.info("extracting %s -> %s", f, out_dir)
        try:
            ext = f.suffix.lower()
            if ext == ".zip":
                with zipfile.ZipFile(f) as zf:
                    zf.extractall(out_dir)
            elif ext == ".7z":
                subprocess.run(["7z", "x", "-y", f"-o{out_dir}", str(f)],
                               check=True, capture_output=True, timeout=600)
            elif ext == ".rar":
                subprocess.run(["unrar", "x", "-y", str(f),
                                str(out_dir) + "/"],
                               check=True, capture_output=True, timeout=600)
            f.unlink()
        except Exception as e:
            log.warning("extract failed %s: %s", f, e)


def _hash_stream(reader):
    """Compute CRC32 + MD5 + SHA1 + size in a single pass over a readable
    stream. Used for both bare files and zip members."""
    crc = 0
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    size = 0
    while True:
        chunk = reader.read(1024 * 1024)
        if not chunk:
            break
        crc = zlib.crc32(chunk, crc)
        md5.update(chunk)
        sha1.update(chunk)
        size += len(chunk)
    return {
        "crc32": f"{crc:08x}",
        "md5":   md5.hexdigest(),
        "sha1":  sha1.hexdigest(),
        "size":  size,
    }


def _platform_rom_exts():
    """All known ROM extensions minus the archive types. Used to find the
    real ROM file inside a .zip / .7z."""
    return plats.all_extensions() - plats.CLASSIFIER_AMBIGUOUS


def hash_rom(path):
    """Compute hashes of the actual ROM bytes. For zipped/7z cartridges,
    we hash the INNER file - no-intro/redump record hashes of the raw
    ROM, never the archive. Returns dict {crc32, md5, sha1, size,
    inner_name} or None on failure."""
    p   = Path(path)
    ext = p.suffix.lower()

    if ext == ".zip":
        try:
            with zipfile.ZipFile(p) as zf:
                rom_exts = _platform_rom_exts()
                # Pick the first member whose extension looks ROM-ish.
                inner = None
                for n in zf.namelist():
                    if Path(n).suffix.lower() in rom_exts:
                        inner = n
                        break
                if not inner:
                    return None
                with zf.open(inner) as f:
                    h = _hash_stream(f)
                h["inner_name"] = inner
                return h
        except Exception as e:
            log.warning("zip hash failed %s: %s", p, e)
            return None

    if ext in {".7z", ".rar"}:
        # No streaming reader for 7z/rar in stdlib; extract to a tmp dir,
        # hash the first ROM-extension file we find, then clean up.
        try:
            with tempfile.TemporaryDirectory(prefix="refinery-hash-") as td:
                if ext == ".7z":
                    subprocess.run(["7z", "x", "-y", f"-o{td}", str(p)],
                                   check=True, capture_output=True,
                                   timeout=600)
                else:
                    subprocess.run(["unrar", "x", "-y", str(p), td + "/"],
                                   check=True, capture_output=True,
                                   timeout=600)
                rom_exts = _platform_rom_exts()
                for f in Path(td).rglob("*"):
                    if (f.is_file()
                            and f.suffix.lower() in rom_exts):
                        with open(f, "rb") as fh:
                            h = _hash_stream(fh)
                        h["inner_name"] = f.name
                        return h
        except Exception as e:
            log.warning("archive hash failed %s: %s", p, e)
        return None

    # Bare file (.nes, .gba, .iso, .bin, .chd, ...)
    try:
        with open(p, "rb") as f:
            return _hash_stream(f)
    except Exception as e:
        log.warning("file hash failed %s: %s", p, e)
        return None


def _strip_region_year(name):
    """Pull '(USA)', '(Europe)', '(1996)' style tags off a no-intro title
    so the displayed title is the bare game name. Returns (clean_title,
    year, region_tag). Year falls back to None if the title doesn't have
    one (no-intro names usually don't, but some do)."""
    if not name:
        return name, None, None
    region = game_dat.region_of(name)
    year_m = re.search(r"\((19\d{2}|20\d{2})\)", name)
    year   = int(year_m.group(1)) if year_m else None
    # Remove all parenthesised tags to get the clean title
    clean  = re.sub(r"\s*\([^)]*\)", "", name).strip()
    clean  = re.sub(r"\s*\[[^\]]*\]", "", clean).strip()
    return clean, year, region


def process_game(folder):
    """Scanner entry point. Phase 2 only - classify + extract + stage one
    item per ROM file with status='ready'. Phase 3 hashes + matches DATs."""
    platform = classify(folder)
    if not platform:
        with db.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO items
                     (media_type, status, source_path, error, processed_at)
                   VALUES ('game', 'failed', ?, ?, datetime('now'))""",
                (folder,
                 "could not determine platform - rename the folder with "
                 "a hint like (PSX), [NES], SNES, GBA, etc."),
            )
        log.warning("game classify failed: %s", folder)
        return None

    log.info("classified game folder as %s: %s", platform, folder)
    extract_disc_archives(folder, platform)

    rom_files = list_rom_files(folder, platform)
    if not rom_files:
        log.warning("no ROM files in %s for platform %s", folder, platform)
        with db.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO items
                     (media_type, status, source_path, subtype,
                      error, processed_at)
                   VALUES ('game', 'failed', ?, ?, ?, datetime('now'))""",
                (folder, platform, "no ROM files matched platform extensions"),
            )
        return None

    plat_name = plats.PLATFORMS[platform]["name"]
    last_id   = None
    for rom_path in rom_files:
        filename_stem = Path(rom_path).stem
        meta = {"platform": platform, "platform_name": plat_name}

        # Hash + DAT lookup. Use canonical name as title when verified;
        # fall back to the filename otherwise.
        hashes = hash_rom(rom_path)
        title  = filename_stem
        year   = None
        match  = None
        verified = False
        if hashes:
            meta["hashes"] = hashes
            match = game_dat.lookup_by_hash(
                crc32=hashes["crc32"],
                md5=hashes["md5"],
                sha1=hashes["sha1"],
                platform=platform,
            )
            if match:
                verified = True
                canonical = match["name"]
                clean_title, ctitle_year, region = _strip_region_year(canonical)
                if clean_title:
                    title = clean_title
                if ctitle_year:
                    year = ctitle_year
                meta["dat_match"] = {
                    "name":   canonical,
                    "region": region,
                    "kind":   match.get("kind"),
                }
                log.info("game DAT match %s -> %s [%s]",
                         filename_stem, canonical, region)
            else:
                log.info("game UNVERIFIED (no DAT match): %s [%s]",
                         filename_stem, platform)
        meta["verified"] = verified

        with db.get_db() as conn:
            cur = conn.execute(
                """INSERT OR REPLACE INTO items
                     (media_type, status, source_path, subtype,
                      title, year, meta_json, processed_at)
                   VALUES ('game', 'ready', ?, ?, ?, ?, ?, datetime('now'))""",
                (rom_path, platform, title, year, json.dumps(meta)),
            )
            last_id = cur.lastrowid
        log.info("staged game id=%d: %s [%s] verified=%s",
                 last_id, title, platform, verified)
    return last_id
