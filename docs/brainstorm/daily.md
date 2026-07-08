 Great direction - the newspaper metaphor is the perfect wrapper because it lets you pack a huge amount
   of real content while giving structure. Real data always wins over fiction, theme is the paper stock
  it's printed on. Here's the design:
     
  Concept: THE ISHIMURA DAILY
     
  CEC-branded newspaper delivered to the ship. Masthead date shows both Earth UTC and "Ship Time" so the
   theme survives without competing for content real estate. Multi-column layout, serif body font,
  section flags, byline attributions to real sources ("From the NOAA Wire", "Via ESA Communiqué"). Every
   piece of content is real - Ishimura is the paper mill, not the source.

  Section layout
  
  Masthead
  - "USG ISHIMURA DAILY - CEC-Approved Information Dispatch"
  - Vol. 3, Edition 247 (auto-increment)
  - Datestamp: "07 JUL 2026 EARTH-STANDARD // 6.34.847 SHIP TIME"
  - Weather box (real, for user's location) + fake ship weather
  
  Front Page (Above-the-fold)
  - Lead story: highest-weight of the day, curated by algorithm or admin pick
  - 3-4 secondary headlines with lede paragraphs
  - Photo/image with fake CEC censor bars over anything questionable (fun)
  - Breaking news ticker at top when it's active
  - "Wire alerts" - persistent bar for major USGS/NOAA/space events

  Section pages (tabs, each feels like turning to page N):

  World
  
  - Reuters/AP/BBC/Al Jazeera RSS aggregated
  - USGS earthquake feed (>M4.5)
  - NOAA severe weather warnings
  - ACLED conflict tracker where accessible
  - NASA FIRMS active wildfires (interactive map)
  - Storm/hurricane tracker (NOAA + JMA)
  - Auto-generated summaries (single para) via cheap LLM
  - Byline: "From the [source] Wire"
  
  Space
 
  Priority real data - your fascination without the fiction:
  - Launches today/this week - Launch Library 2 API, with mission profile: what payload, what agency,
  what mission
  - Currently in orbit - astronaut count + names + their duration + which module
  - Space weather report - Kp index, solar wind speed, X-ray flux, geomagnetic storm level (NOAA SWPC)
  - Aurora forecast - Actual likelihood for user's latitude tonight
  - JWST current target - What the eye is looking at right now, with a paragraph of context
  - NASA APOD - full image + explanation as one prominent column
  - Latest Hubble/JWST release - fresh image of the week with expert-generated summary
  - Voyager 1 + 2 distance report - rolling updated
  - New exoplanets - recent Kepler/TESS confirmations
  - Meteor shower calendar - upcoming peaks with viewing guides for your location
  - Solar events - CMEs detected in the last 24h + expected Earth impact times
  - ISS pass predictor - visible from your location this week
  - Rocket lab op-ed - editorial column: "The Case for Starship's 47th Delay"
  - Ars Technica space RSS

  Sci/Tech

  - Nature, Science, Ars Technica RSS
  - Latest notable arXiv papers (curated categories)
  - Hacker News top 5 with metadata
  - Github trending
  - Recent notable retractions (retractionwatch.com)
 
  Markets

  - Major indices (S&P, Dow, Nasdaq, FTSE, Nikkei)
  - Crypto (CoinGecko)
  - Commodities (gold, oil)
  - Fake CEC company stock "CNCX-B" with fictional ticker action
  - Currency (USD/EUR/JPY/GBP)
  
  Sports (repurposed as Rec Deck Report)
  
  - Chess league standings from Rec Deck
  - Poker night results
  - KF2 wave records 
  - Vintage Story achievements
  - Fika raid outcomes
  - Homelab-wide stats leaderboard for the week

  Weather
  
  - User's local (7-day forecast, radar embed)
  - Global anomalies (extreme temp records set today)
  - Ocean temperatures + coral bleaching alerts
  - Air quality index for your location + major cities
  
  Op-Ed
  
  - Ishimura Bugle editorial (weekly)
  - Rotating Fermi paradox essay
  - User-submitted letters from suggestion box
  - Guest columns (Dr. Kyne's Journal excerpts as regular feature)
  - "Ask the Communications Officer" reader Q&A
  
  Classifieds

  - Open requests service items ("WANTED: Blade Runner 2049 blu-ray rip")
  - Rec Deck challenge board
  - Community suggestions marketplace
  - Hangar server open slots ("KF2 Wave 5 - 2 slots"
  - Movie night scheduler
  
  Comics / Puzzle

  - Daily crossword auto-generated from Ishimura + real-world vocabulary
  - Chess puzzle of the day from Rec Deck
  - CEC safety poster (fake, funny)
  - Random webcomic RSS pull

  Local (Ishimura)

  - Real ops noise dressed up: "REFINERY: 12 items processed. HANGAR: 3 servers nominal."
  - Recent Ship's Log entries (real system events)
  - Discord chatter mirror (opt-in public posts)
  - Recovered logs count community-wide
  - ARG progress bar
  - Discord chatter mirror (opt-in public posts)
  - Recovered logs count community-wide
  - ARG progress bar

  Selfoss-style features to steal

  - Personal edition - each user picks which sections/feeds to include. Their paper is different from another crew member's.
  - Reading progress - articles you've read get grayed out. Unread count per section.
  - Star / save - build a personal archive from any article
  - Full-text search - across all past editions
  - Print mode - clean CSS for actual paper printing (fun for physical takeaway)
  - Reading time estimator per article
  - Section reorder - drag to reprioritize sections in your edition

  Worldmonitor-style features to steal

  - Live event map - interactive world map with active earthquakes/wildfires/conflicts/hurricanes as pins. Click for detail.
  - Live tickers - persistent bottom bar with breaking events streaming
  - Alert threshold system - user sets "notify me for earthquakes > M5.5" - ntfy pushes to their phone
  - Historical replay - "what happened on this day last year" auto-generated section
  - Correlation view - see when multiple event types spike together (solar storm + market drop + earthquake cluster = fun conspiracycontent)

  Newspaper-metaphor originals

  - Daily archive - /edition/2026-07-08 - every past edition browsable, print-preserved
  - Special editions - major event triggers a mid-day extra edition. "EXTRA! EXTRA! Successful Falcon Heavy launch!" Auto-pushed to Discord/ntfy.
  - Anniversary reprints - "Five years ago today's edition" auto-populated
  - Correction column - "Yesterday's edition mislabeled the M6.2 as M6.0. We regret the error." Auto-generated when data updates.
  - Obituaries - Real spacecraft that died recently (Kepler's last transmission, Cassini's Grand Finaleanniversary), themed as shipobituaries
  - Personal ad section - fun user-authored entries between real classifieds
  - CEC Weekly Circulation Report - Total views, most-read stories, print-mode users, weekly stats

  Techstack sketch

  - Flask app on ishimura, one systemd unit
  - SQLite for article cache + user prefs + daily editions
  - Background worker: pull all feeds every 5-15 min
  - Cheap LLM (Ollama on ishimura) for auto-summaries + article dedup
  - Frontend mostly server-rendered HTML with light JS (fits newspaper metaphor, fast, print-friendly)
  - New nix module at modules/nixos/ishimura/daily.nix
  - Subdomain: daily.ishimura.lol or press.ishimura.lol

  Space tab specifically - the priority for you
  
  Since you want the space tab meaningful, front-load these before any narrative fiction:
  
  Live data (always visible, updated 15 min or better):
  1. Space weather status bar (Kp, solar wind, X-ray flux)
  2. Currently in orbit list (astronauts + mission durations)
  3. Next 3 launches with countdown timers + livestream links when active
  4. Current JWST target with context
  
  Daily-refresh content:
  5. NASA APOD prominently
  6. Latest fresh JWST/Hubble/Rover release
  7. Recent exoplanet confirmations
  8. Aurora forecast for tonight (personalized)
  9. Meteor shower status
  10. Space weather forecast (next 3 days)
  
  Weekly features: 
  11. Featured mission deep-dive
  12. Extreme-object spotlight (largest black hole detected, farthest galaxy observed, etc)
  13. Historical space anniversaries this week
  14. Rocket lab / space policy op-ed
  15. Failed mission memorial (rotating spacecraft)
  
  Interactive: 
  16. Solar system view (real positions right now)
  17. Deep space companion tracker (Voyager 1, 2, JWST, New Horizons, Perseverance)
  18. Interactive JWST deep field zoom
  19. Constellation of the night for your location

  Alerts (ntfy): 
  20. CME / geomagnetic storm inbound
  21. Kilonova/supernova detected
  22. Meteor shower peak (24h warning)
  23. Notable launch (30 min warning)
  Local (Ishimura)

  - Real ops noise dressed up: "REFINERY: 12 items processed. HANGAR: 3 servers nominal."
  - Recent Ship's Log entries (real system events)
  - Discord chatter mirror (opt-in public posts)
  - Recovered logs count community-wide
  - ARG progress bar

  Selfoss-style features to steal

  - Personal edition - each user picks which sections/feeds to include. Their paper is different from another crew member's.
  - Reading progress - articles you've read get grayed out. Unread count per section.
  - Star / save - build a personal archive from any article
  - Full-text search - across all past editions
  - Print mode - clean CSS for actual paper printing (fun for physical takeaway)
  - Reading time estimator per article
  - Section reorder - drag to reprioritize sections in your edition

  Worldmonitor-style features to steal

  - Live event map - interactive world map with active earthquakes/wildfires/conflicts/hurricanes as pins. Click for detail.
  - Live tickers - persistent bottom bar with breaking events streaming
  - Alert threshold system - user sets "notify me for earthquakes > M5.5" - ntfy pushes to their phone
  - Historical replay - "what happened on this day last year" auto-generated section
  - Correlation view - see when multiple event types spike together (solar storm + market drop + earthquake cluster = fun conspiracy
  content)

  Newspaper-metaphor originals

  - Daily archive - /edition/2026-07-08 - every past edition browsable, print-preserved
  - Special editions - major event triggers a mid-day extra edition. "EXTRA! EXTRA! Successful Falcon Heavy launch!" Auto-pushed to
  Discord/ntfy.
  - Anniversary reprints - "Five years ago today's edition" auto-populated
  - Correction column - "Yesterday's edition mislabeled the M6.2 as M6.0. We regret the error." Auto-generated when data updates.
  - Obituaries - Real spacecraft that died recently (Kepler's last transmission, Cassini's Grand Finaleanniversary), themed as ship
  obituaries
  - Personal ad section - fun user-authored entries between real classifieds
  - CEC Weekly Circulation Report - Total views, most-read stories, print-mode users, weekly stats

  Techstack sketch

  - Flask app on ishimura, one systemd unit
  - SQLite for article cache + user prefs + daily editions
  - Background worker: pull all feeds every 5-15 min
  - Cheap LLM (Ollama on ishimura) for auto-summaries + article dedup
  - Frontend mostly server-rendered HTML with light JS (fits newspaper metaphor, fast, print-friendly)
  - New nix module at modules/nixos/ishimura/daily.nix
  - Subdomain: daily.ishimura.lol or press.ishimura.lol

  Space tab specifically - the priority for you

  Since you want the space tab meaningful, front-load these before any narrative fiction:

  Live data (always visible, updated 15 min or better):
  1. Space weather status bar (Kp, solar wind, X-ray flux)
  2. Currently in orbit list (astronauts + mission durations)
  3. Next 3 launches with countdown timers + livestream links when active
  4. Current JWST target with context

  Daily-refresh content:
  5. NASA APOD prominently
  6. Latest fresh JWST/Hubble/Rover release
  7. Recent exoplanet confirmations
  8. Aurora forecast for tonight (personalized)
  9. Meteor shower status
  10. Space weather forecast (next 3 days)

  Weekly features:
  11. Featured mission deep-dive
  12. Extreme-object spotlight (largest black hole detected, farthest galaxy observed, etc)
  13. Historical space anniversaries this week
  14. Rocket lab / space policy op-ed
  15. Failed mission memorial (rotating spacecraft)

  Interactive:
  16. Solar system view (real positions right now)
  17. Deep space companion tracker (Voyager 1, 2, JWST, New Horizons, Perseverance)
  18. Interactive JWST deep field zoom
  19. Constellation of the night for your location

  Alerts (ntfy):
  20. CME / geomagnetic storm inbound
  21. Kilonova/supernova detected
  22. Meteor shower peak (24h warning)
  23. Notable launch (30 min warning)
  24. Aurora likely tonight (evening warning)

  24. Aurora likely tonight (evening warning)

  The Ishimura wrapper appears in bylines ("Via CEC Astronomical Bureau") and framing ("SHIP'S
  ASTROMETRY DEPARTMENT REPORTS...") but every number is real.

  Effort estimate

  - Minimum viable newspaper (masthead, 4 sections, RSS aggregation, print CSS): 1 week
  - Full-featured with all sections + personal editions + search: 3 weeks
  - Space tab as designed with 20+ data sources + alerts + interactive elements: 1.5 weeks
  - LLM summarization + auto-editorial + special editions: 1 week additional

  Total: ~5-6 weeks for the whole newspaper as designed, front-loaded so a weekly-satisfying version
  ships early.

  Killer four to ship first

  - Masthead + Front Page + World + Space sections with RSS + real APIs = feels like a paper by day one
  - Ntfy alerts for space weather + earthquakes + notable launches = becomes life infrastructure
  - Daily archive + print mode = the newspaper metaphor pays off immediately
  - Personal edition preferences = each crew member's paper is different, gives them ownership

  Want the spec for The Ishimura Daily as a design doc in notes/specs/?
