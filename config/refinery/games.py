"""Game ROM processor.

Pipeline per download folder:
  1. Classify to a platform slug (extension voting + filename hints).
  2. Extract archived disc images so chdman can later see the BIN/CUE/ISO.
  3. For each ROM file: hash it, look up in the DAT hash cache, look up in
     IGDB for cover / summary / genre, stage one queue row per ROM.

On approve (see write_and_move):
  - Disc-based platforms: chdman convert BIN/CUE / ISO -> CHD when the user
    checks the box. Space savings are large and every serious emulator
    supports CHD.
  - Rename ROM to canonical (or user-edited) title, move under
    <roms>/<platform>/<title>.<ext>.
  - Drop cover.jpg sidecar next to the ROM."""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import zlib
from collections import Counter
from pathlib import Path

import db
import game_dat
import game_igdb
import game_platforms as plats

log = logging.getLogger("refinery.games")

ARCHIVE_EXTS = {".zip", ".7z", ".rar"}

GAME_COVER_DIR = os.environ.get("REFINERY_GAME_COVER_DIR",
                                "/persist/refinery/game_covers")

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

# When multiple platforms share extensions (BIN/CUE = ps1|ps2|saturn|scd|
# pcecd|3do|dc, ISO = many, .bin = md too) and there's no filename hint,
# fall back to this preference order. Prefer the most-common platforms
# so an unlabeled disc rip lands on PS1 (the sane default) instead of 3DO.
PLATFORM_TIEBREAK = [
    "ps1", "ps2", "psp", "gc", "wii", "saturn", "dc", "scd", "pcecd",
    "xbox", "x360", "3do", "gba", "snes", "nes", "n64",
]
_TIEBREAK_INDEX = {slug: i for i, slug in enumerate(PLATFORM_TIEBREAK)}


def _hint_platform(text):
    if not text:
        return None
    # Normalise underscores/dots to spaces so word boundaries in the hint
    # regexes fire on names like "sonic_saturn" or "trap.gunner.psx".
    norm = re.sub(r"[_.]+", " ", text)
    for rx, slug in _HINT_RES:
        if rx.search(norm):
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

    # No hint - take the most-voted, then use PLATFORM_TIEBREAK preference
    # (so an unlabeled BIN/CUE folder lands on PS1, not 3DO). Slugs not in
    # the tiebreak fall to alphabetical for determinism.
    top  = votes.most_common()
    best = top[0][1]
    winners = [slug for slug, n in top if n == best]
    return sorted(winners,
                  key=lambda s: (_TIEBREAK_INDEX.get(s, 999), s))[0]


def _classify_single_file(path):
    """Platform for a single ROM file (retry / reprocess path). Uses the
    file's extension, peeking into archives, plus filename + parent-folder
    hints to disambiguate."""
    p = Path(path)
    ext = p.suffix.lower()
    cands = set()
    if ext in ARCHIVE_EXTS:
        for inner in _peek_archive(p):
            cands.update(plats.for_extension(Path(inner).suffix.lower()))
        cands.update(plats.for_extension(ext))
    else:
        cands.update(plats.for_extension(ext))

    if not cands:
        return None
    if len(cands) == 1:
        return next(iter(cands))

    h = _hint_platform(p.name) or _hint_platform(p.parent.name)
    if h and h in cands:
        return h
    return sorted(cands,
                  key=lambda s: (_TIEBREAK_INDEX.get(s, 999), s))[0]


# For disc-based platforms only these extensions count as "one game". The
# .bin / .wav / .flac / etc. are companion tracks the .cue wraps up. Order
# is preference-descending so a multi-disc pack with a .m3u prefers the m3u.
DISC_PRIMARY_EXTS = (".m3u", ".chd", ".cue", ".gdi", ".iso", ".pbp", ".cdi")


def list_rom_files(folder, platform):
    """Files that look like ROMs for `platform`. For cartridge platforms:
    every matching file is one ROM. For disc platforms: only the primary
    disc-image file per game (cue/m3u/chd/iso/gdi/pbp/cdi) - the .bin and
    .wav companions are wrapped by the .cue and would otherwise stage one
    row per data/audio track."""
    p = Path(folder)
    if not p.is_dir():
        return []
    exts = set(plats.PLATFORMS[platform]["exts"])
    disc_based = plats.PLATFORMS[platform].get("disc_based")
    out  = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if disc_based:
            if ext in DISC_PRIMARY_EXTS and ext in exts:
                out.append(str(f))
            continue
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


def _cue_files(cue_path):
    """Parse the FILE directives out of a .cue. Returns list of Paths in
    the order the cue lists them. Best-effort - unreadable lines or
    missing files are skipped, and if the cue has no FILE lines we fall
    back to sibling .bin files that share the cue's stem."""
    cue = Path(cue_path)
    tracks = []
    try:
        for line in cue.read_text(errors="replace").splitlines():
            m = re.match(r'\s*FILE\s+"?([^"]+)"?\s+\w+', line, re.IGNORECASE)
            if m:
                p = (cue.parent / m.group(1))
                if p.exists():
                    tracks.append(p)
    except Exception:
        pass
    if not tracks:
        stem = cue.stem
        for p in sorted(cue.parent.iterdir()):
            if p.suffix.lower() == ".bin" and p.stem.startswith(stem):
                tracks.append(p)
    return tracks


def hash_rom(path):
    """Compute hashes of the actual ROM bytes. For zipped/7z cartridges,
    we hash the INNER file - no-intro/redump record hashes of the raw
    ROM, never the archive. For .cue we hash the first .bin the cue
    references (that's the data track, which Redump records the hash
    of). Returns dict {crc32, md5, sha1, size, inner_name} or None on
    failure."""
    p   = Path(path)
    ext = p.suffix.lower()

    if ext == ".cue":
        tracks = _cue_files(p)
        if not tracks:
            return None
        try:
            with open(tracks[0], "rb") as f:
                h = _hash_stream(f)
            h["inner_name"] = tracks[0].name
            return h
        except Exception as e:
            log.warning("cue-referenced hash failed %s: %s", tracks[0], e)
            return None

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


def _stage_rom(rom_path, platform):
    """Hash + DAT lookup + IGDB enrichment for one ROM, then insert/replace
    the queue row. Returns the item id."""
    filename_stem = Path(rom_path).stem
    plat_name     = plats.PLATFORMS[platform]["name"]
    igdb_plat     = plats.PLATFORMS[platform].get("igdb_id")
    meta = {"platform": platform, "platform_name": plat_name}

    hashes   = hash_rom(rom_path)
    title    = filename_stem
    year     = None
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
            verified   = True
            canonical  = match["name"]
            clean, ctitle_year, region = _strip_region_year(canonical)
            if clean:
                title = clean
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

    # IGDB enrichment - use the cleanest title we have so far.
    developer = None
    genre     = None
    cover_local = None
    if game_igdb.enabled():
        igdb = game_igdb.search_game(title, igdb_platform_id=igdb_plat)
        if igdb:
            meta["igdb"] = {
                "id":        igdb.get("igdb_id"),
                "name":      igdb.get("name"),
                "summary":   igdb.get("summary"),
                "developer": igdb.get("developer"),
                "publisher": igdb.get("publisher"),
                "genres":    igdb.get("genres"),
                "cover_id":  igdb.get("cover_id"),
            }
            # Only trust IGDB fields where we don't already have DAT truth.
            if not year and igdb.get("year"):
                year = igdb["year"]
            developer = igdb.get("developer") or igdb.get("publisher")
            genre     = igdb.get("genre")
            if igdb.get("cover_id"):
                cover_local = game_igdb.download_cover(
                    igdb["cover_id"], GAME_COVER_DIR)

    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO items
                 (media_type, status, source_path, subtype,
                  title, artist, year, genre, cover_local,
                  meta_json, processed_at)
               VALUES ('game', 'ready', ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (str(rom_path), platform, title, developer, year, genre,
             cover_local, json.dumps(meta)),
        )
        item_id = cur.lastrowid
    log.info("staged game id=%d: %s [%s] verified=%s",
             item_id, title, platform, verified)
    return item_id


def process_game(folder):
    """Scanner entry point. Classify + extract archives + stage one item
    per ROM file. Each ROM row is keyed on the file path so the folder
    placeholder set by the scanner can be safely swept afterward."""
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

    last_id = None
    for rom_path in rom_files:
        last_id = _stage_rom(rom_path, platform)
    return last_id


def process_game_file(path):
    """Single-file entry point used by RETRY / REPROCESS on an already-
    staged row whose source_path is the ROM file itself. Same shape as
    book.process_book_file."""
    p = Path(path)
    if not p.exists():
        return None
    platform = _classify_single_file(p)
    if not platform:
        with db.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO items
                     (media_type, status, source_path, error, processed_at)
                   VALUES ('game', 'failed', ?, ?, datetime('now'))""",
                (str(p),
                 "could not determine platform for single ROM - rename "
                 "the file with a platform hint like (PSX), [NES], etc."),
            )
        return None
    return _stage_rom(str(p), platform)


# ── Approval / write-out ─────────────────────────────────────────────────────

def _safe_path(s):
    if not s:
        return "_"
    s = re.sub(r'[<>:"|?*\\\\/]', "", s).strip()
    return s or "_"


def library_path_for(target_root, platform, title, ext):
    """Where will this ROM land after approve? Used by the conflict warning
    and the writer itself."""
    plat = _safe_path(platform)
    name = _safe_path(title)
    return Path(target_root) / plat / f"{name}{ext}"


# chdman targets:
#   createcd -> for BIN/CUE-based CD platforms
#   createdvd -> for single-track ISO DVD platforms (PS2, GC, Wii, Xbox)
# Everything not listed here we move as-is. In particular PSP UMD (.iso /
# .cso) is skipped: chdman doesn't handle UMD and emulators consume iso/cso
# directly, so conversion would just be lossy destruction.
CHDMAN_CD_PLATFORMS  = {"ps1", "scd", "saturn", "pcecd", "3do", "dc"}
CHDMAN_DVD_PLATFORMS = {"ps2", "gc", "wii", "xbox"}


def _chdman_convert(src_path, platform):
    """Convert a disc image to CHD via chdman. Handles BIN/CUE (createcd)
    and ISO (createdvd) depending on the platform. Returns Path of the
    resulting .chd, or None on failure.

    Callers should pass the .cue for CD or the .iso for DVD - not the .bin
    or track file."""
    src = Path(src_path)
    if not shutil.which("chdman"):
        log.warning("chdman not in PATH")
        return None
    out = src.with_suffix(".chd")

    if platform in CHDMAN_CD_PLATFORMS and src.suffix.lower() == ".cue":
        sub = "createcd"
    elif platform in CHDMAN_DVD_PLATFORMS and src.suffix.lower() == ".iso":
        sub = "createdvd"
    else:
        return None

    cmd = ["chdman", sub, "-i", str(src), "-o", str(out), "-f"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=3600)
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            log.info("chdman: %s -> %s", src.name, out.name)
            return out
        log.warning("chdman failed (rc=%d): %s",
                    r.returncode, r.stderr.decode("utf-8", "ignore")[:400])
    except subprocess.TimeoutExpired:
        log.warning("chdman timeout: %s", src)
    except Exception as e:
        log.warning("chdman error: %s", e)
    return None


def _companion_tracks(cue_path):
    """Files referenced by a .cue that should be cleaned up once chdman
    has folded them into a .chd. Wraps _cue_files and also includes any
    sibling .bin sharing the cue's stem (redundant with _cue_files' own
    fallback but harmless)."""
    tracks = set(_cue_files(cue_path))
    cue = Path(cue_path)
    for p in cue.parent.iterdir():
        if p.suffix.lower() == ".bin" and p.stem.startswith(cue.stem):
            tracks.add(p)
    return sorted(tracks)


def write_and_move(item, target_root, convert_chd=False):
    """Move one game item into the RomM library. For disc images with
    convert_chd, run chdman first and use the .chd as the source.

    - target_root: /mnt/storage/media/roms
    - Landing path: <target_root>/<platform>/<title>.<ext>
    - Drops cover.jpg next to the ROM if we have one."""
    src = Path(item["source_path"])
    if not src.exists():
        raise FileNotFoundError(src)

    platform = item.get("subtype")
    if not platform or platform not in plats.PLATFORMS:
        raise ValueError(f"missing/unknown platform {platform!r} on item")

    disc_based = plats.PLATFORMS[platform].get("disc_based")
    src_ext    = src.suffix.lower()
    companions = []
    chd_source = None

    # Pick the right source to hand chdman when appropriate. For BIN/CUE the
    # user's source_path might be the .bin (that's what the scanner staged);
    # prefer a sibling .cue if one exists.
    if convert_chd and disc_based:
        cue_candidate = None
        if src_ext == ".cue":
            cue_candidate = src
        elif src_ext == ".bin":
            for p in src.parent.iterdir():
                if p.suffix.lower() == ".cue" and p.stem == src.stem:
                    cue_candidate = p
                    break
        iso_candidate = src if src_ext == ".iso" else None
        chd_source = cue_candidate or iso_candidate

    if chd_source is not None:
        converted = _chdman_convert(chd_source, platform)
        if converted and converted.exists():
            if chd_source.suffix.lower() == ".cue":
                companions = _companion_tracks(chd_source)
            src = converted
            src_ext = ".chd"

    title = _safe_path(item.get("title") or src.stem)
    dest  = library_path_for(target_root, platform, title, src_ext)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Sidecar cover.jpg (RomM picks these up).
    if item.get("cover_local") and os.path.exists(item["cover_local"]):
        try:
            with open(item["cover_local"], "rb") as s, \
                 open(dest.parent / f"{title}.jpg", "wb") as d:
                d.write(s.read())
        except Exception as e:
            log.warning("copy game cover failed: %s", e)

    try:
        src.replace(dest)
    except Exception as e:
        log.error("move failed %s -> %s: %s", src, dest, e)
        raise

    # Clean up companion track files (bin/wav/flac) that were folded into
    # the CHD. Only removes files we know were referenced by the .cue.
    for c in companions:
        try:
            if c.exists() and c.resolve() != dest.resolve():
                c.unlink()
        except Exception as e:
            log.warning("companion cleanup failed %s: %s", c, e)

    # Clean up the (now empty) source folder if it was a one-ROM bundle
    try:
        parent = Path(item["source_path"]).parent
        if (parent.exists() and parent != Path(target_root)
                and not any(parent.iterdir())):
            parent.rmdir()
    except Exception:
        pass

    return {"dest": str(dest)}
