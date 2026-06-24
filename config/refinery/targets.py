"""Centralized config of where each media type lands in the library.

Processors call `target_for(media_type[, subtype])` instead of hardcoding paths
or each pulling its own env var. Bucketed media (games-by-platform, anime vs
non-anime, etc.) use the subtype to extend the base path."""

import os


TARGETS = {
    "music":         os.environ.get("REFINERY_MUSIC_TARGET",
                                    "/mnt/storage/media/music"),
    "book":          os.environ.get("REFINERY_BOOK_TARGET",
                                    "/mnt/storage/media/books"),
    "game":          os.environ.get("REFINERY_GAME_TARGET",
                                    "/mnt/storage/media/roms"),
    # Forward-declared; processors arrive later. Env vars exist now so
    # ACLs / persistence can be set up alongside, no scrambling later.
    "movie":         os.environ.get("REFINERY_MOVIE_TARGET",
                                    "/mnt/storage/media/movies"),
    "show":          os.environ.get("REFINERY_SHOW_TARGET",
                                    "/mnt/storage/media/shows"),
    "anime_movie":   os.environ.get("REFINERY_ANIME_MOVIE_TARGET",
                                    "/mnt/storage/media/anime/movies"),
    "anime_show":    os.environ.get("REFINERY_ANIME_SHOW_TARGET",
                                    "/mnt/storage/media/anime/shows"),
    "documentary":   os.environ.get("REFINERY_DOCUMENTARY_TARGET",
                                    "/mnt/storage/media/documentaries"),
    "docuseries":    os.environ.get("REFINERY_DOCUSERIES_TARGET",
                                    "/mnt/storage/media/docuseries"),
    "short_film":    os.environ.get("REFINERY_SHORT_FILM_TARGET",
                                    "/mnt/storage/media/short-films"),
    "fan_edit_film": os.environ.get("REFINERY_FAN_EDIT_FILM_TARGET",
                                    "/mnt/storage/media/fan-edits"),
}


def target_for(media_type, subtype=None):
    """Resolve (media_type[, subtype]) to a destination root.

    For games: subtype = platform slug (psx, snes, gba, ...). Result is
    `<game_target>/<subtype>/`, which matches RomM's expected layout."""
    base = TARGETS.get(media_type)
    if base is None:
        raise KeyError(f"no target configured for media_type={media_type!r}")
    if subtype:
        return os.path.join(base, subtype)
    return base
