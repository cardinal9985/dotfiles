# The Ishimura Daily - CEC Newspaper Design (`daily.ishimura.lol`)

**Status:** design brainstormed 2026-07-08, ready for scope-cut + implementation planning.

**One-liner:** Newspaper-styled dashboard that aggregates real-world RSS + live monitoring APIs (weather, space, seismic, markets, disasters) into a daily edition, wrapped in CEC/Ishimura theming. Every number is real; the paper stock is fictional. Combines the ambition of worldmonitor with the reading experience of selfoss-webfront.

**Why:** The homelab already tracks itself (Grafana, stats, hangar). What's missing is a curated view of the outside world through the same aesthetic lens. A newspaper metaphor gives the site editorial gravity, real ops value (weather, launches, alerts), and evergreen daily content that doesn't require writing anything.

## Guiding principles

- **Real data first, theme as garnish.** Every widget must show real information. Ishimura framing lives in bylines, section names, and small themed sidebars, never in the core content.
- **Newspaper metaphor pays rent.** Daily editions, print mode, sections/columns, byline attributions, archive navigation. If a feature only works because it's a newspaper, it's a keeper.
- **Ambient consumption.** Reading the paper should feel like a morning ritual, not a dashboard-poll. Slow interface, longer content pieces, digest formats.
- **Personal editions.** Every crew member's paper is different based on their subscribed sections and location.
- **Alerts belong to ntfy.** The paper is for reading. Notifications for time-sensitive events (space weather, earthquakes, launches) push to phones via existing ntfy infra.

## Non-goals

- Not a replacement for RSS reader clients (though it is one, that's incidental)
- Not real-time (30-min freshness is fine; special editions can trigger sooner)
- Not user-generated as primary content (editorial submissions are a section, not the point)
- Not comment threads (Discord handles discussion)
- Not paywalled anything - it's a personal homelab paper
- Not a business/financial-heavy paper (markets get a small section, that's it)

## Architecture

### Hosting

New Flask app on ishimura:

- `daily.ishimura.lol` fronted by pangolin with voidauth-forwardauth (public reading, personalization requires login)
- Runs as `daily` systemd user, port `5011`
- Nix module at `modules/nixos/ishimura/daily.nix`
- Persistence at `/persist/daily/` for cache DB + user prefs + archive editions
- Frontend mostly server-rendered HTML with minimal JS (fits newspaper metaphor, print-friendly, fast)

### Data pipeline

Background scheduler (APScheduler like refinery uses) hits each feed on its own cadence:

- **Fast-poll (5 min):** USGS earthquakes, NOAA severe weather alerts, launch countdowns
- **Medium-poll (15 min):** RSS aggregation, space weather (Kp/wind), markets, JWST target
- **Slow-poll (hourly):** APOD, non-breaking news feeds, meteor forecasts
- **Daily (03:00 ship time):** rebuild the day's edition, snapshot to archive, generate front-page layout

Cached in SQLite. Edition rendering pulls from cache, not upstream. If upstream is down for a few hours, paper still publishes.

### LLM assistance

Local Ollama on ishimura (small model, ~7B is enough for summaries) for:

- Article auto-summarization (single-paragraph blurbs for long feeds)
- Feature story stitching (2-3 related RSS items composed into one longer piece)
- Duplicate detection (same story from 4 wires becomes one grouped item)
- Editorial titles (fresh headline generation for republished pieces)

Runs as a background job at edition time, not on-request. Costs zero human effort per edition.

### Techstack

- Python + Flask + APScheduler + SQLite + feedparser + requests
- Cheap Ollama for summarization (already available on ishimura or fresh install)
- Server-rendered HTML with light JS (progressively enhanced)
- Print CSS mode for the newspaper metaphor
- Nix module + sops for API keys (NASA, weather providers, etc.)

## Sections

Each section is one URL that renders as a "page" of the paper. Front page pulls highlights from all sections.

### Front page

- Masthead: "USG ISHIMURA DAILY - CEC-approved information dispatch"
- Date: `07 JUL 2026 EARTH-STANDARD // 6.34.847 SHIP TIME`
- Edition number auto-incremented
- Lead story (algorithm-picked or admin-curated)
- 3-4 secondary headlines with ledes
- Weather box (user-local + fake ship weather)
- Wire alerts persistent bar for major events
- Section index

### World

Real-time global monitoring, worldmonitor DNA:

- USGS earthquakes (>M4.5)
- NOAA severe weather warnings
- NASA FIRMS active wildfires
- Storm/hurricane tracker (NOAA + JMA)
- Reuters/AP/BBC/Al Jazeera RSS aggregated + LLM-summarized
- ACLED conflict tracker (if accessible)
- Interactive world event map with pins
- Sentiment meter (aggregated sentiment of the day's headlines)

### Space (priority feature)

Priority is live real data, no fictional Ishimura position claims. Ishimura wrapper is in bylines only ("Via CEC Astronomical Bureau").

**Live (updated 15 min):**

- Space weather status bar (Kp index, solar wind speed, X-ray flux)
- Currently in orbit list (astronauts + mission names + durations)
- Next 3 launches with countdown timers + livestream links when active
- Current JWST target with one-paragraph context

**Daily refresh:**

- NASA APOD prominently displayed with full explanation
- Latest fresh JWST/Hubble/rover image release with expert-generated summary
- Recent exoplanet confirmations
- Aurora forecast for user's latitude
- Meteor shower status
- Space weather forecast (next 3 days)

**Weekly features:**

- Featured mission deep-dive
- Extreme-object spotlight (largest black hole, farthest galaxy, oldest photon)
- Historical space anniversaries this week
- Rocket lab / space policy op-ed column
- Failed mission memorial (rotating spacecraft obituaries)

**Interactive:**

- Solar system view (real positions right now)
- Deep space companion tracker (Voyager 1/2, JWST, New Horizons, Perseverance) with comm delays
- Interactive JWST deep field zoom
- Constellation of the night for user's location

**Alerts (via ntfy):**

- CME / geomagnetic storm inbound
- Kilonova/supernova detected
- Meteor shower peak (24h warning)
- Notable launch (30 min warning)
- Aurora likely tonight (evening warning)

### Weather (also priority)

More than a forecast. Uses NOAA, OpenWeather (or similar), NASA FIRMS, USGS, and specialized sources.

**Multi-location dashboard:**

- User's own location + subscribed friend cities visible at once
- Comparison anomalies ("Baghdad is 5°C hotter than your city")

**Global monitoring:**

- Extreme records set today (hottest, coldest, wettest globally)
- Marine heatwave alerts + coral bleaching status
- Arctic + Antarctic sea ice extent (daily minimum vs. historical)
- Drought monitor (US + European drought observatory)
- Wildfire tracker (NASA FIRMS)
- Storm/hurricane globally with cones + JMA coverage

**Editorial + trivia:**

- This day in weather history ("1938: New England Hurricane made landfall")
- Historical comparison ("Today's high 3°C above your region's date average")
- Weather anomaly of the week

**Practical:**

- 7-day forecast for user's location with radar embed
- Air quality index + pollen + UV
- Sunset/sunrise with golden hour + blue hour for photographers
- Astronomical viewing conditions (cloud coverage + moon phase + light pollution class)
- Marine conditions (wave heights, water temp) for coastal users

**Live windows:**

- Aggregated live webcam wall (curated worldwide feeds)

**Themed sidebar:**

- Fake Ishimura ship weather ("Aegis Sector: -270°C, minor solar wind") that doesn't compete with real forecast

### Sci/Tech

- Nature, Science, Ars Technica RSS
- Latest notable arXiv papers (user-curated categories)
- Hacker News top 5 with metadata
- Github trending repos
- Recent retractions from Retraction Watch

### Markets (small section)

- Major indices (S&P, Dow, Nasdaq, FTSE, Nikkei)
- Crypto via CoinGecko free tier
- Commodities (gold, oil)
- Currency (USD/EUR/JPY/GBP)
- Fake CEC company stock "CNCX-B" moving on internal server activity

### Rec Deck Report (Sports)

- Chess league standings from Rec Deck
- Poker + Blackjack results
- KF2 wave records
- Vintage Story achievements
- Fika raid outcomes
- Homelab-wide weekly stats leaderboard

### Op-Ed

- Ishimura Bugle weekly editorial (auto + curated)
- Rotating Fermi paradox essay
- User-submitted letters from suggestion box
- Dr. Kyne's Journal excerpts (in-universe recurring column)
- Ask the Communications Officer (Q&A)
- Ask the Captain (monthly admin Q&A)

### Classifieds

- Open requests items ("WANTED: Blade Runner 2049 rip")
- Rec Deck challenge board
- Community suggestions marketplace
- Hangar server open slots
- Movie night scheduler poll

### Release Calendar

Filtered to what the crew actually cares about. Not a firehose of every TMDB release.

- Upcoming movie/TV releases from TMDB filtered by the requests service's wanted list + Refinery's monitored series
- Upcoming game releases from IGDB filtered by ROM library platforms + wishlist
- Upcoming book releases from OpenLibrary/Google Books filtered by BookLore's followed authors
- Month view (default) + week view + list view
- Personalized: users see their own wanted items plus optionally the crew's aggregated interests
- Icons per media type + provider badge
- Direct link to submit a request (deep-link into requests.ishimura.lol prefilled)
- Ntfy push 24h before a wanted item's release date

Data flows from Refinery's wanted-list module (see refinery-arr spec) + Requests' pending list. Daily just renders.

### Now Streaming Aboard

Front-page live widget showing current crew activity across services.

- Jellyfin `/Sessions` API for active video streams (title, user, elapsed/remaining)
- Navidrome (or its successor) Subsonic API for current music playback
- Hangar `/public/status` for players in game servers
- Rec Deck live matches
- Opt-in per user (privacy respected)
- Real-time-ish (30s refresh, WebSocket if we want to spend the effort later)
- Compact card layout: avatar + service icon + what they're consuming
- Persistent block on front page above the fold when 1+ crew active, hidden when 0
- Not stored - purely a view over live APIs. No history here (that's stats' domain).

### Comics + Puzzle

- Daily crossword auto-generated from that day's articles
- Chess puzzle of the day from Rec Deck
- CEC safety poster (rotating themed lore)
- Random webcomic RSS

### Local (Ishimura)

- Real ops noise dressed as CEC dispatches ("REFINERY: 12 items processed. HANGAR: 3 servers nominal.")
- Recent Ship's Log entries
- Discord chatter mirror (opt-in public posts)
- Recovered logs count community-wide (ARG progress bar)

## Cross-cutting features

### Personal edition system

- Users pick which sections + feeds appear in their edition
- Users set location for local weather + astronomy
- Users set friend cities for the multi-location weather dashboard
- Section reorder (drag-to-prioritize)
- Reading progress tracked (read articles gray out, unread counts per section)
- Star/save articles into personal archive
- Full-text search across own saved archive

### Archive + memory

- Daily archive: `/edition/2026-07-08` shows any past edition print-preserved
- Anniversary reprints: "Five years ago today's edition" auto-populated
- Time capsule: front page from 1/5/10 years ago on this date
- Time-travel mode: browse past editions in original layout

### Special editions

Auto-triggered by major events, cross-posted to Discord + ntfy:

- Major spacecraft launch success/failure
- Rare kilonova/supernova detection
- Notable earthquake (>M7)
- Major hurricane landfall
- Significant political events (elections, major geopolitical developments)
- Local homelab milestones (Hangar 1000 uptime days, refinery 10k items)

### Reading modes

- Standard web layout
- Print mode (clean CSS, actual paper-friendly)
- Reader mode (single-article, auto-scroll at reading pace)
- Passive listening mode (TTS reads today's edition aloud)
- Podcast digest (auto-generated 8-min audio summary, downloadable)

### Interactive extras

- Prediction market: fake bets on real events using Rec Deck tickets. Track user accuracy.
- Editorial submissions with community upvoting for op-ed spot
- The Question: one poll per day for the crew
- Weekly puzzle hunt spanning multiple sections

### Ambient

- Background printing press + teletype audio (opt-in)
- Ambient CEC intercom chime when major breaking news lands (opt-in, tab-open only)
- Ambient theme choices: standard newspaper, wartime bulletin, corporate memo

### Alerts (ntfy integration)

Push to phone via existing ntfy infra:

- Space: CME inbound, kilonova detected, meteor shower peak, launch imminent, aurora tonight
- Weather: severe weather warning for user location, extreme record broken globally
- World: major earthquake (>M6.5) anywhere, hurricane landfall imminent
- Ishimura: server outages, refinery failures worth flagging
- Editorial: your saved-topic tag has a new front-page article

User configures alert threshold + which categories they subscribe to.

## Stages

**Total effort estimated at 5-6 weeks front-loaded so a satisfying MVP ships in week 1.**

### Stage 1 - MVP paper (1 week)

- `daily.ishimura.lol` up
- Masthead + front page + 4 sections: World, Space, Weather, Local
- RSS aggregation for World section (Reuters, BBC, Al Jazeera)
- Space section with launches + space weather + APOD + JWST target
- Weather section with user location forecast + 3 global widgets (heat records, aurora, meteor)
- Local section with Ship's Log + Hangar status
- Daily edition rendering + archive
- Print CSS mode

Deliverable: readable morning paper by day 7.

### Stage 2 - Personalization + more sections (1 week)

- User login + preferences (voidauth integration)
- Section subscription system
- Location-based content wiring
- Sci/Tech + Markets + Rec Deck Report sections
- Star/save archive
- Section reorder

### Stage 3 - Alerts + ntfy (3-5 days)

- Space weather + earthquake + hurricane + launch alerts
- Per-user threshold config
- Discord bot integration for special editions

### Stage 4 - Interactive + gamified (1 week)

- Interactive world event map (worldmonitor DNA)
- Interactive JWST deep field zoom
- Solar system view
- Deep space companion tracker
- Prediction market
- Daily crossword generator

### Stage 5 - Editorial + LLM (1 week)

- Op-Ed section with user submissions + upvoting
- LLM auto-summarization pipeline (Ollama)
- Feature story stitching (multi-source composition)
- Daily podcast digest (TTS)
- Fermi essay rotation
- Failed mission memorial

### Stage 6 - Polish + ambient (3-5 days)

- Print CSS refinement
- Reader mode + passive listening
- Ambient audio + intercom chimes
- Anniversary + time capsule features
- Special edition automation
- Live webcam wall

## Data sources catalog

| Category | Source | Access | Notes |
|---|---|---|---|
| News RSS | Reuters, AP, BBC, Al Jazeera, Ars Technica | free | RSS |
| Space imagery | NASA APOD API | free key | daily |
| Launches | Launch Library 2 | free | 15 min |
| Space weather | NOAA SWPC | free | 5-15 min |
| Astronaut/orbit | Open Notify | free | hourly |
| Earthquakes | USGS FDSN | free | 5 min |
| Weather | OpenWeather / NOAA NWS | free tier / free | 15 min |
| Wildfires | NASA FIRMS | free | 15 min |
| Storms | NOAA NHC + JMA | free | 15 min |
| Air quality | AirNow (US) + WAQI (global) | free tier | hourly |
| Exoplanets | NASA Exoplanet Archive | free | daily |
| Markets | Yahoo Finance scrape | free | 15 min |
| Crypto | CoinGecko | free tier | 15 min |
| Retractions | Retraction Watch RSS | free | daily |
| arXiv | arXiv API | free | daily |
| Hacker News | HN API | free | 15 min |
| Github trending | GH RSS/scrape | free | hourly |

## Open questions

- **LLM cost/latency:** Ollama on ishimura sufficient? Local model quality for summarization + feature stitching? Might need to benchmark.
- **Alert threshold defaults:** what's a sensible ntfy alert threshold for earthquakes? (probably >M6.5 globally, >M4.5 in user's country)
- **User geo:** how do we set user location? Profile field? IP-derived with override? Consent flow needed.
- **Comment/reaction UX:** ruled out for MVP but keep the door open for a "reactions" system (limited emoji set) on articles.
- **Print archiving:** should each daily edition be preservable as PDF for physical archiving? Fun but effort.
- **Advertiser slots:** the fake CEC ads throughout - how many, how absurd, how to rotate them cleanly.

## Ties into

- [[hangar]] - local section pulls from Hangar's `/public/status`
- [[stats]] - Rec Deck Report + featured crew activity comes from stats
- [[refinery]] - "new arrivals" widget for local section
- [[crew hub]] - user profile page cross-references daily reading history
- [[audio log ARG]] - ARG progress bar + community meta-puzzle status in Local section
- [[Discord comms bot]] - special editions cross-post to #ship-log, alerts cross-post to Discord

## Killer wins to prioritize

If we can only build 5 things in the first month:

1. **MVP paper (Stage 1)** with World + Space + Weather + Local sections. This alone is the biggest daily-use win.
2. **Ntfy alerts** for space weather, earthquakes, launches. Transforms the paper from a reading page into life infrastructure.
3. **Personal edition preferences.** Makes it feel like *your* paper, not a generic feed.
4. **Print mode + daily archive.** Sells the newspaper metaphor completely and takes ~1 day to build.
5. **Special editions on major events.** Rare but memorable. Cross-post to Discord for the community effect.
