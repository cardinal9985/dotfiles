
  1. Watchlist / Ratings (list.ishimura.lol) - Movies/shows/games/books you want or finished, with ratings + notes. Pairs with requests (prospective) and stats (retrospective). Prevents "did I already watch this?" ~3 evenings.
  2. Feed Reader (feeds.ishimura.lol) - RSS/Atom + YouTube channels + Twitch VODs. Marks as read when refinery ingests a matching file. ~4-5 evenings.
  3. Recipe Book (recipes.ishimura.lol) - Personal cookbook, tag search, meal planning, grocery-list export. ~4-5 evenings.
  4. Notes / Personal Wiki (notes.ishimura.lol) - Turn the notes/ dir into a queryable wiki with backlinks + daily notes. Ingest markdown from git so both worlds coexist. ~5-7 evenings.
  5. Podcast Player (pods.ishimura.lol) - Subscribe to feeds, auto-download into refinery inbox, web player, ties into Navidrome/stats. ~3-4 evenings.
  6. Photo Gallery (photos.ishimura.lol) - Immich alternative reading /mnt/storage/media/photos/. Thumbnails, EXIF, album folders. Refinery can stage phone dumps. ~1 week.
  7. Bookmarks (bm.ishimura.lol) - Tag-based, full-text-searchable, per-URL screenshot, Reader Mode extract on save. ~3 evenings.
  8. Shopping / Todo shared lists - Cross-device with WebSocket sync + per-list share tokens so friends don't need accounts. ~2 evenings.
  9. Guest book / Photo diary - Fun social touch for visitors to ishimura.lol. ~2 evenings.
  10. Achievement aggregator - Stats++ that pulls Steam / EFT-SPT / Vintage Story / KF2 progress into one leaderboard. ~1-2 weeks.
  
Self-tracking / quantified self 
     
  11. Habit tracker - Daily checkboxes, streak counter, feeds Stats. ~2 evenings.
  12. Fitness log - Sets/reps/PRs for lifting, or run tracker. Weight over time. Manual entry keeps it dead simple. ~3 evenings.
  13. Mood check-in - One-tap 1-10 + optional note, aggregates into Stats. ~1 evening.
  14. Sleep tracker - Manual bedtime/wake or import from watch. ~2 evenings.
  15. Book quote log - Capture passages while reading, tag by book. Refinery could stage a "quotes" media type. ~2 evenings.
  
  Household / life admin

  16. Home inventory - Appliances, electronics, model numbers, warranty dates, receipt photos. Huge for insurance claims. ~3-4 evenings.
  17. Vehicle service log - Odometer, oil changes, tire rotations, receipt scans, calendar reminders via ntfy. ~2-3 evenings.
  18. Gift ideas tracker - Per-person running list. Pair with birthday reminders (ntfy 2 weeks out). ~2 evenings.
  19. Kitchen dashboard - Meant to be pulled up on a wall tablet: this week's meal plan, chore rotation, household reminders, weather. ~3-4 evenings.
  20. Guest WiFi QR generator - Rotates a temp wifi code, generates a QR page you show visitors. ~1 evening.
 
  Financial

  21. Expense tracker - Manual entry (safer than bank APIs), category budgets, monthly reports. ~4-5 evenings.
  22. Subscription tracker - What am I paying monthly? When does the free trial end? Ntfy alert 3 days before charges. ~2 evenings.

  Homelab / infra

  23. Backup verification dashboard - Every volume: last backup, size, hash check status. Extends the borg hangar plan. ~2-3 evenings.
  24. Public status page - StatusPage-lite. Shows friends/users what's up + a scheduled maintenance calendar. ~2-3 evenings.
  25. Certs / domain / license expiry board - Countdown timers, ntfy 30/7 days out. ~1-2 evenings.
  26. Pangolin route inventory - All subdomains at a glance, their auth level, cert status. Kind of a self-audit. ~2 evenings.
  27. DNS stats dashboard - Complement to AdGuard: most-blocked, per-device breakdown, top talkers. ~2 evenings.
 
  Social / communication

  28. Movie/game night scheduler - Post a poll ("watch X on Fri"), friends vote, top choice gets a calendar invite + ntfy. ~3 evenings.
  29. Guest photo album - Anonymous share link where friends upload photos to a shared album (parties, trips). No account required. ~2-3 evenings.
  30. Private URL shortener + read-later - ish.mu/abc redirects. Optional "public reading list" showing what you're currently into. ~2 evenings.

  Content / media adjacent
 
  31. VOD archiver - Point at YouTube/Twitch channels, auto yt-dlp new uploads through refinery. ~3 evenings.
  32. Manga/comic reader - CBR/CBZ streaming from /mnt/storage/media/comics/. Reading progress synced across devices. ~3-4 evenings.
  33. Meal photo journal - Different from recipe book - "what did I eat this week?" Feeds Stats. ~2 evenings.
  
  Meta / control-plane
  
  34. Data-flow cockpit - One view of the whole media pipeline: slskd complete → refinery queue → Jellyfin/Navidrome/RomM/BookLore. What's stuck where. ~3-4 evenings.
  35. Personal search engine - Full-text across your notes, mail archives, docs, bookmarks. Like Recoll but web + your data. ~1 week.
  
  Fun

  36. Ship's log / captain's diary - Themed daily-journal specifically for ishimura roleplay. Auto-generated entries from system events ("2026-07-08 - Refinery processed 12 items. KF2 uptime 4 days."). Fits the Dead Space vibe. ~2 evenings.
  37. Achievement showcase page - Public wall of your gaming/reading/media achievements. Trophy case. ~2 evenings.
  
    Deep theme (immersive/atmospheric)

  1. RIG Profiles - Each user has a Dead Space-style Resource Integration Gear page. Health bar =
  current media streak, mood ring = based on their listening habits, "biosign" = login recency, kinesis
  level = how many services they've engaged with. Themed leaderboard. Ties into Stats. ~1 week.
  2. Audio log discovery - Hidden text/audio logs scattered across the site (a page corner, a 404 easter
   egg, inside Hangar's about section). Users click to collect them into a personal "recovered logs"
  library. Each log is a lore fragment - CEC memos, Dr. Kyne's journal, mining reports, ominous crew
  notes. Long-tail engagement + reward for exploration. ~4-5 evenings.
  3. Marker terminal - Cryptic ARG puzzle terminal accessed from a hidden URL. Solving small puzzles
  (Dead Space math ciphers, logic locks, "unmake me whole" wordplay) unlocks lore fragments, badges, or
  backdoor access to hidden features. Community-solved over weeks/months. ~1-2 weeks initial + ongoing
  puzzle design.
  4. Interactive ship deck map - Homepage replacement. Visitors see a top-down Ishimura schematic; click
   Bridge for admin services, Hangar for game servers, Medical Bay for stats, Hydroponics for something
  goofy, etc. Sections gray out if service is down. Some rooms behind achievements. ~1 week.
  5. Necromorph incursion alerts - Random atmospheric warnings appearing site-wide: "Necromorph detected
   in Deck 4 - avoid area" (broken /admin link joke), "quarantine lifted" when a stuck backup completes.
   Just flavor overlays, no actual mechanics. ~2 evenings.

  Roleplay / community

  6. Crew roster - Users pick a "position" at signup (Engineer, Security, Medical, Science, Miner,
  Recreation Officer). Position dictates their badge, some UI hints, maybe minor permissions or
  exclusive views. Aliases show as Sec/MaxwellPayne. ~3-4 evenings.
  7. Ship intercom - Themed shared bulletin/chat. CEC letterhead formatting, timestamps in fake
  shipboard dating, static/interference effects on old messages. Async, but the intercom "chirps" when
  someone posts. ~4-5 evenings.
  8. Anonymous suggestion box - Physical-looking terminal on the site where users drop ideas/complaints
  anonymously into a CEC-branded "employee feedback" queue. Admin reviews later. Nice for a homelab that
   friends actually use. ~2 evenings.
  9. Ishimura Bugle - Auto-generated monthly newsletter. Top-watched media, most-active crew, new mods
  installed on game servers, latest recovered logs. Emailed or dropped in the intercom. ~3-4 evenings.

  Games / cross-service loops

  10. Necromorph hunt - Cross-service scavenger event. Necromorph glyphs randomly appear on Jellyfin,
  Hangar, refinery, homepage. Clicking one earns rec-deck tickets. Rare golden ones (Regenerator!) award
   bigger rewards. Recurs weekly/monthly. Ties existing services together as a game. ~3-4 evenings.
  11. Zero-G plasma cutter range - Small browser game with the Dead Space plasma cutter reticle.
  Score-based leaderboard. Simple but fits theme perfectly. ~4-5 evenings.
  12. Mining idle game - Each crew member has a mining claim. Ore accumulates over real-time hours,
  spent on RIG cosmetics/badges/gift shop. Login just to check your mine = habit hook. ~1 week.
  13. Cargo bay heist co-op - Themed multiplayer minigame where a small group races to grab crates
  before decompression. Real-time via WebSocket. ~1-2 weeks.

  10. Necromorph hunt - Cross-service scavenger event. Necromorph glyphs randomly appear on Jellyfin, Hangar, refinery, homepage. Clicking one earns rec-deck tickets. Rare golden ones (Regenerator!) award bigger rewards. Recurs weekly/monthly. Ties
  existing services together as a game. ~3-4 evenings.
  11. Zero-G plasma cutter range - Small browser game with the Dead Space plasma cutter reticle. Score-based leaderboard. Simple but fits theme perfectly. ~4-5 evenings.
  12. Mining idle game - Each crew member has a mining claim. Ore accumulates over real-time hours, spent on RIG cosmetics/badges/gift shop. Login just to check your mine = habit hook. ~1 week.
  13. Cargo bay heist co-op - Themed multiplayer minigame where a small group races to grab crates before decompression. Real-time via WebSocket. ~1-2 weeks.

  Ship's-log style journaling

  14. Ship's log (auto+manual) - Auto-populated with system events ("2026-07-08 - Refinery processed 12 items. Vintage Story uptime 4 days. Two crew joined KF2 raid."), user-editable with personal entries. Public-facing so friends can see the ship's
  history. Fits the Dead Space captain's-log aesthetic perfectly. ~3 evenings.
  15. Recovered database logs - When users watch/listen/read something, an auto-generated "database entry" is added to their personal RIG in-lore ("Analysis complete. Subject: Blade Runner 2049. Verdict: [user rating]. Notes: [user notes]"). Their
  personal Necronomicon of media. ~3-4 evenings.

  Utility with theme

  16. Life support panel - Personal health/wellness tracker (habits, mood, sleep) but themed as your RIG biosign monitor. Same functionality as a habit tracker but way more fun to check. ~4 evenings.
  17. Kinesis dashboard - Drag-drop UI where each user "grabs" widgets (their favorite services, stats, achievements) and arranges their personal deck. Kinesis module aesthetic. ~4-5 evenings.

  If I had to pick the killer three

  - Audio log discovery - ambient reward-for-exploration, extends site's replay value, evergreen.
  - Interactive ship deck map - one-time high-impact redesign that reframes the whole homepage as a place instead of a menu.
  - Necromorph hunt - ties everything together into a shared cross-service game with real rewards.
