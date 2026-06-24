"""Game platform taxonomy. Slugs match RomM / IGDB conventions so files
land at the right path for RomM to pick up.

Each entry:
  slug:         folder slug under /mnt/storage/media/roms/<slug>/
  name:         human-readable for the UI
  exts:         file extensions that identify a ROM for this platform
                (used as the primary classification signal)
  disc_based:   True if multi-track CDs / multi-disc games are common
  needs_bios:   True if a BIOS file is required to emulate
  igdb_id:      IGDB platform id (for metadata lookup)
  dat_source:   "nointro" (cartridges) or "redump" (discs); some are both
  ra_console:   RetroAchievements console_id, or None if RA unsupported"""

PLATFORMS = {
    # Nintendo - cartridges
    "nes":      {"name": "NES",              "exts": [".nes", ".unf", ".unif"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 18, "dat_source": "nointro", "ra_console": 7},
    "snes":     {"name": "Super Nintendo",    "exts": [".smc", ".sfc", ".swc", ".fig"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 19, "dat_source": "nointro", "ra_console": 3},
    "n64":      {"name": "Nintendo 64",       "exts": [".n64", ".z64", ".v64", ".u64"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 4,  "dat_source": "nointro", "ra_console": 2},
    "gb":       {"name": "Game Boy",          "exts": [".gb"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 33, "dat_source": "nointro", "ra_console": 4},
    "gbc":      {"name": "Game Boy Color",    "exts": [".gbc"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 22, "dat_source": "nointro", "ra_console": 6},
    "gba":      {"name": "Game Boy Advance",  "exts": [".gba"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 24, "dat_source": "nointro", "ra_console": 5},
    "nds":      {"name": "Nintendo DS",       "exts": [".nds"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 20, "dat_source": "nointro", "ra_console": 18},
    "3ds":      {"name": "Nintendo 3DS",      "exts": [".3ds", ".cci", ".cia"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 37, "dat_source": "nointro", "ra_console": 62},
    "gc":       {"name": "GameCube",          "exts": [".gcm", ".gcz", ".iso", ".rvz"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 21, "dat_source": "redump",  "ra_console": 16},
    "wii":      {"name": "Wii",               "exts": [".wbfs", ".wad", ".iso", ".rvz"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 5,  "dat_source": "redump",  "ra_console": None},
    "wiiu":     {"name": "Wii U",             "exts": [".wux", ".wud"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 41, "dat_source": "redump",  "ra_console": None},
    "switch":   {"name": "Switch",            "exts": [".nsp", ".xci", ".nca"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 130, "dat_source": "nointro", "ra_console": None},
    "vb":       {"name": "Virtual Boy",       "exts": [".vb", ".vboy"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 87, "dat_source": "nointro", "ra_console": 28},

    # Sony
    "ps1":      {"name": "PlayStation",       "exts": [".cue", ".bin", ".chd", ".iso", ".pbp", ".m3u"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 7,  "dat_source": "redump",  "ra_console": 12},
    "ps2":      {"name": "PlayStation 2",     "exts": [".iso", ".chd", ".bin", ".cue"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 8,  "dat_source": "redump",  "ra_console": 21},
    "ps3":      {"name": "PlayStation 3",     "exts": [".iso", ".pkg"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 9,  "dat_source": "redump",  "ra_console": None},
    "psp":      {"name": "PSP",               "exts": [".iso", ".cso", ".pbp"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 38, "dat_source": "redump",  "ra_console": 41},
    "vita":     {"name": "PS Vita",           "exts": [".vpk", ".psv"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 46, "dat_source": "nointro", "ra_console": None},

    # Microsoft
    "xbox":     {"name": "Xbox",              "exts": [".iso", ".xiso"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 11, "dat_source": "redump",  "ra_console": None},
    "x360":     {"name": "Xbox 360",          "exts": [".iso", ".xex", ".god"],
                 "disc_based": True,  "needs_bios": False,
                 "igdb_id": 12, "dat_source": "redump",  "ra_console": None},

    # Sega
    "sms":      {"name": "Master System",     "exts": [".sms"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 64, "dat_source": "nointro", "ra_console": 11},
    "gg":       {"name": "Game Gear",         "exts": [".gg"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 35, "dat_source": "nointro", "ra_console": 15},
    "md":       {"name": "Genesis/Mega Drive","exts": [".md", ".smd", ".gen", ".bin"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 29, "dat_source": "nointro", "ra_console": 1},
    "32x":      {"name": "Sega 32X",          "exts": [".32x"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 30, "dat_source": "nointro", "ra_console": 10},
    "scd":      {"name": "Sega CD",           "exts": [".cue", ".bin", ".chd", ".iso"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 78, "dat_source": "redump",  "ra_console": 9},
    "saturn":   {"name": "Saturn",            "exts": [".cue", ".bin", ".chd", ".iso", ".mds"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 32, "dat_source": "redump",  "ra_console": 39},
    "dc":       {"name": "Dreamcast",         "exts": [".cdi", ".gdi", ".chd", ".iso"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 23, "dat_source": "redump",  "ra_console": 40},

    # Atari
    "2600":     {"name": "Atari 2600",        "exts": [".a26"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 59, "dat_source": "nointro", "ra_console": 25},
    "5200":     {"name": "Atari 5200",        "exts": [".a52"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 66, "dat_source": "nointro", "ra_console": 50},
    "7800":     {"name": "Atari 7800",        "exts": [".a78"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 60, "dat_source": "nointro", "ra_console": 51},
    "lynx":     {"name": "Atari Lynx",        "exts": [".lnx", ".lyx"],
                 "disc_based": False, "needs_bios": True,
                 "igdb_id": 61, "dat_source": "nointro", "ra_console": 13},
    "jaguar":   {"name": "Atari Jaguar",      "exts": [".j64", ".jag"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 62, "dat_source": "nointro", "ra_console": 17},

    # NEC / Hudson
    "pce":      {"name": "PC Engine/TG-16",   "exts": [".pce"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 86, "dat_source": "nointro", "ra_console": 8},
    "pcecd":   {"name": "PC Engine CD",       "exts": [".cue", ".bin", ".chd"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 150, "dat_source": "redump", "ra_console": 76},

    # SNK
    "neogeo":   {"name": "Neo Geo",           "exts": [".neo"],
                 "disc_based": False, "needs_bios": True,
                 "igdb_id": 80, "dat_source": "nointro", "ra_console": 24},
    "ngp":      {"name": "Neo Geo Pocket",    "exts": [".ngp", ".ngc"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 119, "dat_source": "nointro", "ra_console": 14},

    # Bandai
    "ws":       {"name": "WonderSwan",        "exts": [".ws", ".wsc"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 57, "dat_source": "nointro", "ra_console": 53},

    # 3DO
    "3do":      {"name": "3DO",               "exts": [".iso", ".chd", ".cue", ".bin"],
                 "disc_based": True,  "needs_bios": True,
                 "igdb_id": 50, "dat_source": "redump",  "ra_console": 43},

    # Arcade (MAME)
    "arcade":   {"name": "Arcade (MAME)",     "exts": [".zip"],
                 "disc_based": False, "needs_bios": False,
                 "igdb_id": 52, "dat_source": "nointro", "ra_console": 27},
}


def for_extension(ext):
    """Return list of platform slugs that claim this extension. Many
    extensions are ambiguous (.iso, .bin, .cue, .zip), so callers need to
    use other signals (filename hints, header bytes, archive contents) to
    disambiguate."""
    ext = (ext or "").lower()
    if not ext.startswith("."):
        ext = "." + ext
    return [slug for slug, p in PLATFORMS.items() if ext in p["exts"]]


def all_extensions():
    """Flat set of every extension we recognise as game-related."""
    return {e for p in PLATFORMS.values() for e in p["exts"]}
