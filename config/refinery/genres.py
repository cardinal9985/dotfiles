"""Collapse arbitrary genre tags (from Bandcamp, MusicBrainz, Last.fm, embedded
ID3, etc.) into a single top-level bucket. Score = sum of matching keyword
lengths so a 'post-rock' tag prefers Post-Rock over Rock."""

TOP_GENRES = {
    "Acoustic":      ["acoustic", "singer-songwriter"],
    "Ambient":       ["ambient", "drone", "dark ambient", "new age"],
    "Blues":         ["blues"],
    "Children's":    ["children", "kids", "nursery"],
    "Christian":     ["christian", "gospel", "ccm", "worship", "praise"],
    "Classical":     ["classical", "baroque", "orchestral", "opera",
                      "symphony", "chamber", "romantic era"],
    "Comedy":        ["comedy", "parody", "novelty"],
    "Country":       ["country", "bluegrass", "americana",
                      "honky-tonk", "outlaw country"],
    "Disco":         ["disco", "boogie", "nu-disco"],
    "Drum & Bass":   ["drum and bass", "dnb", "d&b", "drum n bass",
                      "jungle", "neurofunk"],
    "Dubstep":       ["dubstep", "brostep", "riddim"],
    "Electronic":    ["electronic", "electronica", "synth",
                      "leftfield", "downtempo"],
    "Experimental":  ["experimental", "noise", "avant-garde",
                      "musique concrete", "harsh noise"],
    "Folk":          ["folk", "anti-folk", "freak folk",
                      "neofolk", "indie folk"],
    "Funk":          ["funk", "funky", "g-funk", "p-funk"],
    "Future Funk":   ["future funk"],
    "Gothic":        ["gothic", "goth rock", "gothic rock"],
    "Hardcore":      ["hardcore"],
    "Hip-Hop":       ["hip hop", "hip-hop", "rap", "trap", "boom bap",
                      "drill", "cloud rap", "mumble rap"],
    "House":         ["house", "deep house", "tech house",
                      "electro house", "progressive house"],
    "IDM":           ["idm", "intelligent dance"],
    "Indie":         ["indie"],
    "Industrial":    ["industrial", "ebm", "aggrotech"],
    "J-Pop":         ["j-pop", "jpop", "japanese pop", "j-rock", "j rock"],
    "Jazz":          ["jazz", "bebop", "swing", "smooth jazz",
                      "free jazz", "fusion", "nu jazz"],
    "K-Pop":         ["k-pop", "kpop", "korean pop"],
    "Latin":         ["latin", "salsa", "merengue", "reggaeton",
                      "tango", "bossa nova", "cumbia"],
    "Lofi":          ["lofi", "lo-fi", "lo fi", "chillhop", "lofi hip hop"],
    "Math Rock":     ["math rock", "math-rock", "mathcore"],
    "Metal":         ["metal", "doom", "death", "black metal", "thrash",
                      "grindcore", "sludge", "stoner", "djent",
                      "metalcore", "deathcore", "nu metal", "power metal",
                      "speed metal", "symphonic metal", "folk metal",
                      "viking metal", "drone metal"],
    "New Wave":      ["new wave"],
    "Phonk":         ["phonk", "drift phonk"],
    "Pop":           ["pop", "dream pop", "art pop", "synthpop",
                      "synth-pop", "indie pop", "electropop",
                      "bedroom pop", "city pop", "hyperpop"],
    "Post-Punk":     ["post-punk", "post punk", "darkwave", "coldwave"],
    "Post-Rock":     ["post-rock", "post rock"],
    "Punk":          ["punk", "punk rock", "pop punk", "skate punk",
                      "anarcho", "emo", "screamo", "crust punk",
                      "anarcho punk"],
    "R&B":           ["r&b", "rnb", "rhythm and blues", "soul",
                      "neo-soul", "motown", "doo-wop"],
    "Reggae":        ["reggae", "dub", "roots reggae", "dancehall"],
    "Rock":          ["rock", "grunge", "alternative", "shoegaze",
                      "garage", "psychedelic", "blues rock", "classic rock",
                      "hard rock", "soft rock", "prog rock",
                      "progressive rock", "stoner rock",
                      "krautrock", "surf rock"],
    "Ska":           ["ska"],
    "Soundtrack":    ["soundtrack", "score", "ost"],
    "Video Game Soundtracks": ["video game music", "video game soundtrack",
                               "video game ost", "vgm", "game soundtrack",
                               "game music", "chiptune", "8-bit music",
                               "8bit music", "fakebit"],
    "Film Soundtracks":       ["film score", "film soundtrack", "film ost",
                               "movie soundtrack", "motion picture soundtrack",
                               "cinematic score", "movie score"],
    "Anime Soundtracks":      ["anime soundtrack", "anime ost",
                               "anime score", "anime opening", "anime ending"],
    "Synthwave":     ["synthwave", "outrun", "retrowave", "darksynth"],
    "Techno":        ["techno", "minimal techno", "industrial techno"],
    "Trance":        ["trance", "psytrance", "goa trance", "uplifting trance"],
    "Trip-Hop":      ["trip hop", "trip-hop", "triphop"],
    "Vaporwave":     ["vaporwave", "vapor wave", "mallsoft"],
    "World":         ["world", "afrobeat", "afro", "celtic", "flamenco",
                      "ethnic", "klezmer", "balkan"],
}

ALL = sorted(TOP_GENRES.keys())

# Book genres / subject categories. Free-text input with this as autocomplete,
# matching the music flow (anything OpenLibrary returns can also be entered).
BOOKS = sorted([
    "Art",
    "Biography",
    "Business",
    "Children's",
    "Classics",
    "Comics",
    "Computers",
    "Cooking",
    "Drama",
    "Education",
    "Essays",
    "Fantasy",
    "Fiction",
    "Graphic Novel",
    "Health",
    "Historical Fiction",
    "History",
    "Horror",
    "Humor",
    "Light Novel",
    "Literary Fiction",
    "Manga",
    "Mathematics",
    "Memoir",
    "Mystery",
    "Mythology",
    "Nonfiction",
    "Philosophy",
    "Poetry",
    "Politics",
    "Psychedelics",
    "Psychology",
    "Reference",
    "Religion",
    "Romance",
    "Science",
    "Science Fiction",
    "Self-Help",
    "Short Stories",
    "Spirituality",
    "Technology",
    "Textbook",
    "Thriller",
    "Travel",
    "True Crime",
    "Young Adult",
])


def _norm(s):
    return (s or "").lower().replace("-", " ").replace("_", " ").strip()


def normalize(tags):
    """Take a list of arbitrary genre strings, return single top-level
    bucket. Returns None when nothing matches."""
    if not tags:
        return None
    scores = {}
    for raw in tags:
        t = _norm(raw)
        if not t:
            continue
        for top, keywords in TOP_GENRES.items():
            for kw in keywords:
                if _norm(kw) in t:
                    scores[top] = scores.get(top, 0) + len(kw)
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]
