● Layered ideas, grouped so you can pick a direction:

  Structural expansion (multi-page)
     
  3. RIG Profile pages - Every user has a /crew/<username> page: their crew position, badges, recovered
  log count, current media on Jellyfin/Navidrome, rank, achievements. Public unless opted out.
  4. Recovered Database - /database - each user's own log library viewer. Public log counts, private
  content.
  5. Ship's Log public feed - /log - auto-generated + curated ship events in chronological ticker. Great
   "we exist" page for casual visitors.
  6. Crew roster page - /crew - member gallery with positions, ranks, join dates. Discord-integrated
  presence dots.
  7. Ishimura Bugle archive - /bugle - archive of weekly newsletters.
  8. Achievement showcase - /wall - trophy case of crew accomplishments.
  9. Deck 5 (secret area) - Behind ARG progression. Contains puzzles, hidden games, lore fragments not
  otherwise accessible.
  
  Live widgets for the homepage
  
  10. Crew presence indicator - "3 crew currently aboard: @Maxwell (Deck 4 - Jellyfin), @friend (Hangar
  - KF2), @other (Recreation - Chess)." Shows what everyone's doing without doxxing specific titles
  unless they opt in.
  11. Live activity ticker - Rolling text: "Refinery approved 'X'... KF2 hit wave 6... Vintage Story
  autosaved... 12 tracks scrobbled today..." Very Star Trek LCARS vibe.
  12. Currently consuming - Small block of who's watching/listening what right now (public feed from
  Stats).
  13. System vitals panel - Fake CEC RIG readouts backed by real Prometheus data. Reactor power = CPU
  load, hull integrity = disk health, life support = memory usage. Themed dressing on real ops.
  14. Convergence countdown - When ARG endgame timer is running, big prominent countdown block.
  Empty/hidden otherwise.
  15. Marker signal strength - Cryptic percentage meter that ticks up as crew discovers logs. Community
  progress bar for ARG.
  16. Cargo manifest - Recent Refinery arrivals ticker: last 10 items processed, with tiny covers.
  17. Ship weather - Random fake weather for whatever "sector" of space the ship is in. "Sector 47:
  Micrometeor showers. Radiation nominal." Refreshes daily. Just flavor.
  18. Random recovered log - One log fragment displayed on homepage, changes on refresh. Sampled from
  the corpus.
  19. Crew intercom snippet - Latest public bulletin from Discord/intercom bot, mirrored.
  20. Now streaming - If SyncTube session is active, shows it prominently as "COMMS ACTIVE."
 
  Personalization

  21. Kinesis widgets - Drag-and-drop layout: users pick which widgets to see on their homepage.
  Persisted per user. Kinesis-module UX (grab, drop) fits the theme.
  22. Personal greeting - "Welcome back, Engineer 2nd class MaxwellPayne. Log Rating 3. Last shift: 4
  hours ago." Time-of-day + crew position sensitive.
  23. Highlighted services - User's most-used services get badge treatment on their homepage.
  24. Personal deck map lens - Sections you frequent glow subtly. Unvisited sections dim.
  25. Boot animation - First visit each session: 3-second CEC OS boot sequence loading their profile.
  Can be skipped/disabled.
  
  Theming depth (atmosphere)

  26. CRT + interlace refinement - Add slight vertical hold drift, occasional lines, chromatic
  aberration edges. The existing crt effect goes further.
  27. Interference bursts - Rare (1% of loads) show 200ms static overlay + "SIGNAL LOST - RECONNECTING."
   Bugs out ARG glyphs randomly.
  28. Ambient audio (opt-in) - Ship hum background loop, distant clanks, occasional PA static. Big
  toggle. Sells the atmosphere hard when enabled.
  29. Elevator transitions - Navigating between decks plays a 1-second tram animation with UI slide.
  Feels like moving in a place.
  30. Alert overlays - When a service actually goes down, page top gets an amber CEC alert bar.
  "MAINTENANCE ADVISORY: Deck 3 offline (Jellyfin)." Themes real ops.
  31. Dead pixel randomization - Very rare, one pixel stays lit somewhere for a few seconds. Adds "this
  thing is old" feeling.
  32. Terminal cursor - Cursor becomes a plasma-cutter reticle on interactive elements. Small but very
  Dead Space.
  33. 404 sold hard - Current 404 is text, but could be "SECTION SEALED - HULL BREACH DETECTED" with
  themed graphic. Every 10th 404 drops a log (ARG hook).
  34. BSOD-Ishimura - Deliberate maintenance/error screens that look like a CEC diagnostic panel.
  Repurposes the ugly reality of "something broke" into flavor.
  
  Community features 
  
  35. Public bulletin board - Front-and-center: pinned announcements, upcoming events, "next movie
  night: Thursday." Everyone reads it.
  36. Guest book - Visitors can leave notes. CEC "shore leave register" formatting. Public wall.
  37. Suggestion box - Anonymous feedback drop. Themed as employee feedback tube.
  38. Ship's mood meter - Aggregated crew Mood check-ins visible as a percentage bar. Community wellness
   signal.
  39. Now-playing wall - Grid of small tiles showing what crew is watching/listening. Real-time.
  40. Recent recovered logs highlight - "Crew member @X recovered a fragment from Deck 4." Public feed.
  41. Necromorph sightings ticker - When someone clicks an ARG glyph, small sighting alert. "Sector 3
  sighting reported."

  Practical UX

  42. Global search bar - Cross-service search from homepage: Jellyfin + Navidrome + BookLore + RomM +
  Refinery + logs. Single input.
  43. Command palette - Ctrl+K opens a text-only command interface: "/watch Blade Runner", "/request
  Aliens", "/status". Terminal power-user experience that fits theme perfectly.
  44. Floating quick-access dock - Persistent bottom bar with most-used services. Themed as RIG bottom
  UI.
  45. Keyboard shortcuts - g h = hangar, g j = jellyfin, etc. Discoverable via ?.
  46. Mobile polish - Ship deck map collapses cleanly to a vertical stack on phone.
  47. PWA install - Homepage becomes installable app. Icon = Ishimura badge.
  48. Progressive enhancement - Static HTML still works with JS off. Advanced widgets require it but
  core browsing doesn't.
  
  Content depth
 
  49. CEC company intranet feel - Fake HR notices, safety posters, mining tips scattered around.
  "Reminder: report any unusual dreams to Medical." Every corner has a bit of flavor.
  50. Kyne journal drops - Random pages get a "Dr. Kyne's Journal - Entry 47" snippet. Free lore
  infusion.
 
  If I had to pick a killer five for maximum impact per hour

  - Interactive ship deck map replacing the current grid - single change with biggest atmospheric ROI
  - Live crew presence + activity ticker - makes the site feel alive
  - Public Ship's Log page - free content, works with automation you'll already have
  - Global command palette (Ctrl+K) - terminal-style navigation that fits theme AND is genuinely useful
  - Ambient audio toggle + CRT depth refinement - atmosphere upgrade that costs nothing but sells
  everything else harder

  Want to spec any of these? The deck map is probably the biggest "wow" if we start there.
