# BookLore Replacement - Ebook Library (`books.ishimura.lol`)

**Status:** design 2026-07-09. Replaces both BookLore + Calibre with a single Ishimura-themed reader/library, Kobo sync, guest reading mode.

**One-liner:** Self-hosted ebook library that does everything BookLore + Calibre together do: EPUB/PDF/MOBI/AZW3/CBZ/CBR upload + reader, per-user reading progress synced across devices, OPDS feed, Kobo device sync, guest share links for individual books.

**Why:** BookLore's UI can't be themed to match ishimura; Calibre-Web is heavy Docker + Python2 legacy. Same DIY pattern as refinery/requests/hangar - Python + Flask + SQLite fits the fleet.

## Non-goals

- Not a purchasing storefront
- Not multi-tenant SaaS (household scale)
- Not AI-generated summaries as a primary feature (nice-to-have)

## Architecture

- Flask on ishimura, port `5013`, nix module `modules/nixos/ishimura/library.nix`
- Persistence `/persist/library/library.db` + `/mnt/storage/media/books/{author}/{title}.{ext}`
- Voidauth-forwardauth; guest share tokens bypass voidauth for specific book URLs only
- Reader is client-side JS (epub.js for EPUB, PDF.js for PDF, custom for CBZ/CBR)

## Data model

```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,          -- JSON array
    series TEXT,
    series_index REAL,
    year INTEGER,
    language TEXT,
    isbn TEXT,
    open_library_id TEXT,
    google_books_id TEXT,
    tags TEXT,                      -- JSON array
    description TEXT,
    cover_local TEXT,
    file_path TEXT NOT NULL,
    file_format TEXT NOT NULL,      -- epub, pdf, mobi, azw3, cbz, cbr
    file_size INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_books_author ON books(authors);
CREATE INDEX idx_books_series ON books(series);

CREATE TABLE reading_progress (
    username TEXT NOT NULL,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    cfi TEXT,                       -- epub.js CFI position OR page number for PDF
    percent REAL,                   -- 0.0-1.0
    finished_at TIMESTAMP,
    started_at TIMESTAMP,
    last_read_at TIMESTAMP,
    device TEXT,                    -- "web", "kobo:libra2", etc.
    PRIMARY KEY (username, book_id)
);

CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    cfi TEXT,
    note TEXT,
    highlighted_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shelves (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(username, name)
);

CREATE TABLE shelf_books (
    shelf_id INTEGER REFERENCES shelves(id) ON DELETE CASCADE,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (shelf_id, book_id)
);

CREATE TABLE guest_shares (
    token TEXT PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    created_by TEXT NOT NULL,
    expires_at TIMESTAMP,
    max_reads INTEGER,
    reads_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Features

- **Upload + metadata fetch** - accepts EPUB/PDF/MOBI/AZW3/CBZ/CBR; auto-populates via ISBN/OpenLibrary/Google Books; manual override
- **In-browser reader** - epub.js for EPUB (progress, bookmarks, highlights, font size, theme swap), PDF.js for PDF, custom canvas viewer for CBZ/CBR (page-by-page + thumbnails)
- **Reading progress + bookmarks** - synced per-user across devices; picks up where left off
- **Shelves** - per-user tags (Currently Reading, Favorites, TBR, custom)
- **Series browser** - grouped by series with reading order
- **OPDS feed** at `/opds` - standard catalog for Moon+ Reader, KOReader, etc.
- **Kobo sync** - implements Kobo's proprietary sync API (mimics Kobo Store) so plugging a Kobo device syncs library + progress. Reference: [kobo-sync spec](https://pgaskin.net/kobo-sync/) / [Calibre-Web's Kobo implementation](https://github.com/janeczku/calibre-web/wiki/Kobo-Sync)
- **Guest reading mode** - admin creates share token for a specific book (`/share/<token>`) with optional expiry + max-reads. Reader loads without voidauth. Rate-limited by token, not IP.
- **Full-text search** across metadata + tags
- **Export** - download original file or convert on-the-fly (calibre-cli under the hood if we bundle it, or just serve original)
- **Cover extraction** - pull cover art from EPUB manifest / PDF first page / CBZ first image on import

## Stages

1. **MVP (1 week)** - upload, metadata, library index, epub.js reader, per-user progress, shelves
2. **PDF + CBZ readers (3-5 days)** - PDF.js integration, CBZ/CBR canvas viewer
3. **OPDS + Kobo sync (1 week)** - OPDS 1.2 catalog, Kobo sync API implementation
4. **Guest shares + search (3-5 days)** - share tokens, full-text search
5. **Refinery integration (2-3 days)** - Refinery's book processor imports directly into library instead of dropping files in `/mnt/storage/media/books`

## Ties into

- [[refinery-arr]] - book intake pipeline; approve flow POSTs to library service instead of dropping files
- [[stats-extension]] - reading events feed taste profile + achievements
- [[daily]] - "currently reading aboard" widget

## Open questions

- Kobo sync API is unofficial - keeps working across firmware versions but has to be reverse-engineered on each Kobo update. Fine for personal use, brittle if it breaks
- Calibre convert on-the-fly - bundle calibre-cli or skip? Bundle if size (few hundred MB) is acceptable
