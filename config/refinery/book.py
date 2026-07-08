"""Book processor: read existing metadata (EPUB only, others pass-through),
look up on OpenLibrary, fetch cover, stage in approval queue. On approve,
write tags back (EPUB), rename to Author/Title.ext, move to BookLore root."""

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import requests as http

import db

try:
    from ebooklib import epub
except ImportError:
    epub = None

log = logging.getLogger("refinery.book")

BOOK_EXTS = {".epub", ".pdf", ".mobi", ".azw", ".azw3", ".cbz", ".cbr"}

# Formats Calibre converts to EPUB well (real ebook formats with structured
# text). PDF conversion is hit-or-miss because PDFs are layout-fixed, so it's
# opt-in via the form checkbox on the edit page. Comics (cbz/cbr) we leave
# alone - they're image archives, EPUB doesn't help.
AUTO_CONVERT_EXTS = {".mobi", ".azw", ".azw3"}

BOOK_COVER_DIR = os.environ.get("REFINERY_BOOK_COVER_DIR",
                                "/persist/refinery/book_covers")

OL_BASE   = "https://openlibrary.org"
OL_COVERS = "https://covers.openlibrary.org"

USER_AGENT = "ishimura-refinery/1.0 (https://refinery.ishimura.lol)"


def _http_get(url, params=None, timeout=15):
    try:
        r = http.get(url, params=params, timeout=timeout,
                     headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r
    except Exception as e:
        log.warning("HTTP %s failed: %s", url, e)
        return None


# ── Filename parsing fallback ────────────────────────────────────────────────

def parse_from_filename(stem):
    """'Author - Title' / 'Author_Title' / 'Title' → dict."""
    s = stem.strip()
    if " - " in s:
        a, t = s.split(" - ", 1)
        return {"author": a.strip(), "title": t.strip()}
    if "_-_" in s:
        a, t = s.split("_-_", 1)
        return {"author": a.replace("_", " ").strip(),
                "title": t.replace("_", " ").strip()}
    return {"title": s}


# ── EPUB metadata ────────────────────────────────────────────────────────────

def read_epub_metadata(path):
    if epub is None:
        return {}
    try:
        b = epub.read_epub(str(path))

        def first(ns, key):
            v = b.get_metadata(ns, key)
            return v[0][0] if v else None

        title  = first("DC", "title")
        author = first("DC", "creator")
        date   = first("DC", "date")
        year   = date[:4] if date else None
        descr  = first("DC", "description")
        lang   = first("DC", "language")
        subjects = [s[0] for s in b.get_metadata("DC", "subject") or []]
        return {
            "title":       title,
            "author":      author,
            "year":        year,
            "language":    lang,
            "description": descr,
            "subjects":    subjects,
        }
    except Exception as e:
        log.warning("epub read failed %s: %s", path, e)
        return {}


def convert_to_epub(input_path, cover_path=None, item=None):
    """Convert a non-EPUB ebook to EPUB via Calibre's ebook-convert.
    Embeds the cover and writes basic tags in the same pass. Returns Path
    of the new .epub on success, else None."""
    if not shutil.which("ebook-convert"):
        log.warning("ebook-convert not in PATH")
        return None
    input_path = Path(input_path)
    out = input_path.with_suffix(".epub")

    cmd = ["ebook-convert", str(input_path), str(out)]
    if cover_path and os.path.exists(cover_path):
        cmd += ["--cover", cover_path]
    if item:
        if item.get("title"):  cmd += ["--title",   item["title"]]
        if item.get("artist"): cmd += ["--authors", item["artist"]]
        if item.get("year"):   cmd += ["--pubdate", str(item["year"])]
        if item.get("genre"):  cmd += ["--tags",    item["genre"]]

    try:
        r = subprocess.run(cmd, capture_output=True, timeout=600)
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            log.info("converted %s -> %s", input_path.name, out.name)
            return out
        log.warning("ebook-convert failed (rc=%d): %s",
                    r.returncode, r.stderr.decode("utf-8", "ignore")[:300])
    except subprocess.TimeoutExpired:
        log.warning("ebook-convert timeout: %s", input_path)
    except Exception as e:
        log.warning("ebook-convert error: %s", e)
    return None


def _embed_epub_cover(path, cover_path):
    """Embed cover image into an EPUB via ebooklib."""
    if epub is None or not cover_path or not os.path.exists(cover_path):
        return
    try:
        b = epub.read_epub(str(path))
        with open(cover_path, "rb") as f:
            b.set_cover("cover.jpg", f.read())
        epub.write_epub(str(path), b)
    except Exception as e:
        log.warning("cover embed failed %s: %s", path, e)


def write_epub_metadata(path, item):
    if epub is None:
        return
    try:
        b = epub.read_epub(str(path))
        # Clear & set core fields
        for k in ("title", "creator", "date", "subject"):
            b.metadata.setdefault("http://purl.org/dc/elements/1.1/", {})[k] = []
        if item.get("title"):
            b.set_title(item["title"])
        if item.get("artist"):
            b.add_author(item["artist"])
        if item.get("year"):
            b.add_metadata("DC", "date", str(item["year"]))
        if item.get("genre"):
            b.add_metadata("DC", "subject", item["genre"])
        epub.write_epub(str(path), b)
    except Exception as e:
        log.warning("epub write failed %s: %s", path, e)


def read_book_metadata(path):
    ext = path.suffix.lower()
    if ext == ".epub":
        meta = read_epub_metadata(path)
        if meta.get("title"):
            return meta
    return parse_from_filename(path.stem)


# ── OpenLibrary lookup ───────────────────────────────────────────────────────

def openlibrary_search(title, author=None):
    if not title:
        return None
    params = {"title": title, "limit": 1}
    if author:
        params["author"] = author
    r = _http_get(f"{OL_BASE}/search.json", params=params)
    if not r:
        return None
    try:
        docs = (r.json() or {}).get("docs") or []
    except Exception:
        return None
    if not docs:
        return None
    d = docs[0]
    return {
        "title":      d.get("title"),
        "author":     ", ".join((d.get("author_name") or [])[:2]),
        "year":       d.get("first_publish_year"),
        "cover_id":   d.get("cover_i"),
        "subjects":   (d.get("subject") or [])[:5],
        "ol_key":     d.get("key"),
        "isbn":       (d.get("isbn") or [None])[0] if d.get("isbn") else None,
    }


def download_cover(cover_id, dest_dir):
    if not cover_id:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{cover_id}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    try:
        r = http.get(f"{OL_COVERS}/b/id/{cover_id}-L.jpg",
                     headers={"User-Agent": USER_AGENT},
                     timeout=30, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return dest
    except Exception as e:
        log.warning("cover download failed: %s", e)
        return None


# ── Listing book files in a download folder ──────────────────────────────────

def list_book_files(folder):
    """Walk folder for book files, in stable order."""
    return sorted(
        p for p in Path(folder).rglob("*")
        if p.is_file() and p.suffix.lower() in BOOK_EXTS
    )


# ── Top-level processing ─────────────────────────────────────────────────────

def process_book_file(path, source_path=None):
    """Process ONE book file. Each file becomes its own queue item so the
    user can approve different books from a single bundle separately."""
    path = Path(path)
    if not path.exists():
        return None
    embedded = read_book_metadata(path)

    ol = openlibrary_search(embedded.get("title"), embedded.get("author"))

    final_title  = embedded.get("title")  or (ol and ol.get("title"))
    final_author = embedded.get("author") or (ol and ol.get("author"))
    final_year   = embedded.get("year")   or (ol and ol.get("year"))

    # Genre: prefer embedded subject, then OL first subject
    final_genre = None
    if embedded.get("subjects"):
        final_genre = embedded["subjects"][0]
    elif ol and ol.get("subjects"):
        final_genre = ol["subjects"][0]

    cover_local = None
    if ol and ol.get("cover_id"):
        cover_local = download_cover(ol["cover_id"], BOOK_COVER_DIR)

    meta = {
        "embedded":     embedded,
        "openlibrary":  ol,
        "format":       path.suffix.lower().lstrip("."),
    }

    # source_path uniquely identifies items - use the file path itself so the
    # already-seen check works per book file.
    with db.get_db() as conn:
        item_id = db.upsert_item(conn,
            media_type   = "book",
            status       = "ready",
            source_path  = str(path),
            title        = final_title,
            artist       = final_author,
            year         = int(final_year) if str(final_year or "").isdigit() else None,
            genre        = final_genre,
            cover_local  = cover_local,
            meta_json    = json.dumps(meta),
            processed_at = db.now_utc(),
        )

    log.info("Staged book id=%d: %s - %s", item_id, final_author, final_title)
    return item_id


def process_book(folder):
    """Entry point from scanner. Walks folder, processes each book file."""
    files = list_book_files(folder)
    if not files:
        log.warning("no book files in %s", folder)
        return None
    last_id = None
    for f in files:
        last_id = process_book_file(f, source_path=folder)
    return last_id


# ── Approval / write-out ─────────────────────────────────────────────────────

def _safe_path(s):
    if not s:
        return "_"
    s = re.sub(r'[<>:"|?*\\\\/]', "", s).strip()
    return s or "_"


def library_path_for(target_root, author, title, year=None):
    """Where will this book land after approve? Used by conflict warning."""
    author_dir = _safe_path(author or "Unknown Author")
    title_seg  = _safe_path(title or "Unknown")
    if year:
        title_seg = f"{title_seg} ({year})"
    return Path(target_root) / author_dir / title_seg


def write_and_move(item, target_root, convert_pdf=False):
    """Author/Title (Year).ext - drop cover.jpg next to it.
    Converts MOBI/AZW(/PDF if opted in) to EPUB, embeds the OL cover,
    cleans up tags."""
    src = Path(item["source_path"])
    if not src.exists():
        raise FileNotFoundError(src)

    cover = item.get("cover_local")

    # Format conversion pass
    ext = src.suffix.lower()
    if ext in AUTO_CONVERT_EXTS or (ext == ".pdf" and convert_pdf):
        converted = convert_to_epub(src, cover, item)
        if converted and converted.exists():
            try:
                src.unlink()  # delete the original
            except Exception:
                pass
            src = converted
            ext = ".epub"
            log.info("using converted EPUB: %s", src.name)

    author = _safe_path(item.get("artist") or "Unknown Author")
    title  = _safe_path(item.get("title")  or src.stem)
    if item.get("year"):
        title = f"{title} ({item['year']})"

    dest_dir = Path(target_root) / author
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{title}{ext}"

    # Tag cleanup + cover embed (only meaningful for EPUB)
    if ext == ".epub":
        write_epub_metadata(src, item)
        _embed_epub_cover(src, cover)

    # Sidecar cover
    if item.get("cover_local") and os.path.exists(item["cover_local"]):
        try:
            with open(item["cover_local"], "rb") as s, \
                 open(dest_dir / "cover.jpg", "wb") as d:
                d.write(s.read())
        except Exception as e:
            log.warning("copy cover failed: %s", e)

    try:
        src.replace(dest)
    except Exception as e:
        log.error("move failed %s -> %s: %s", src, dest, e)
        raise

    # Clean up the (empty) source folder if it was a one-book bundle
    try:
        parent = src.parent
        if parent.exists() and parent != Path(target_root) and not any(parent.iterdir()):
            parent.rmdir()
    except Exception:
        pass

    return {"dest": str(dest)}

    return str(dest_dir)
