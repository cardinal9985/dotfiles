● Discord as an extension of the ship rather than a separate space. Here's how I'd hook it in:

  The core bridge - "Comms Officer"
 
  One primary bot (Python + discord.py, running on ishimura as a systemd unit under the same stats or
  new comms user) that acts as the ship's public-address system. Everything flows through it, configured
   per-channel. Foundation for everything below.
  
  Identity + roles (do these first, everything else needs it)

  1. Voidauth ↔ Discord link - Slash command /link DMs you a one-time code that binds your Discord
  account to your voidauth user. Bot now knows who's who across all services.
  2. Crew roles auto-sync - Discord roles mirror voidauth groups (admins, moderators, crew, visitor).
  Position roles from the crew roster idea sync automatically (Engineer, Security, Medical...).
  3. Rank up - As users hit stats milestones or ARG log counts, their Discord role updates. "Rating 3 →
  Rating 2 promotion" ping.
  
  Live service bridging (Ishimura → Discord)
 
  4. Ship's Log auto-poster - New #ship-log channel gets themed system events: "2026-07-08 03:14 -
  Refinery processed 8 items. Vintage Story uptime 6 days. Crew member @Maxwell approved 'The Batman
  (2022)'." Real ops noise dressed as CEC log entries.
  5. Hangar player pings - "@MaxwellPayne connected to Killing Floor 2 - 1/6 slots occupied. Join at
  games.ishimura.lol:7777." Optional per-user opt-out.
  6. Media additions channel - #new-arrivals gets a preview embed when Jellyfin/Navidrome/BookLore/RomM
  gets new content. Cover art, description, direct link.
  7. Requests fulfilled - "@user your request 'Blade Runner 2049' has been added." Ties into your
  existing requests service.
  8. Refinery decisions feed - Just admins - shows what got approved/rejected/failed with a quick
  actions row.
  9. Server incidents - When Hangar/Refinery/Jellyfin goes down or comes back up, a themed status
  message. "MEDICAL BAY OFFLINE - Jellyfin unavailable." Uses Prometheus/Grafana alerts if you've got
  them.
 
  Interactive commands (Discord → Ishimura)
 
  10. /request <movie|show|book|game> - Full-featured request flow inline, no need to visit
  requests.ishimura.lol.
  11. /server <name> <start|stop|status> - Auth-checked against Hangar polkit whitelist. Only admins can
   power-cycle.
  12. /now-playing [@user] - Shows what user's currently watching/listening/reading. Stats-backed.
  13. /stats [@user] - Personal stats card. Last 7 days, top artists, media hours.
  14. /library search <query> - Cross-service search: Jellyfin + Navidrome + BookLore + RomM. Result
  embed with direct links.
  15. /chess @user - Challenges user to a rec deck match. Bot posts an embed with the game link + accept
   button.
  16. /moodist <preset> - Starts a moodist session for whoever's in your voice channel.
  17. /paste - Quickly creates a PrivateBin link from a modal - handy in tech-support conversations.
  
  Dynamic voice channels

  18. Auto-created game rooms - When Hangar detects 2+ players on KF2/VS/Tarkov, bot creates "🎮 Killing
   Floor 2 - Wave 3" voice channel. Deleted when everyone leaves.
  19. Movie night rooms - /movienight <title> polls the crew, top choice at the vote time auto-creates a
   SyncTube session + a voice channel for chatter.
  20. Themed static VCs - Bridge, Cargo Bay, Medical Bay, Hangar. Named to fit the ship.
  
  ARG integration

  21. Log discovery announcements - Anonymized cryptic: "A crew member has recovered a fragment from
  Deck 4." Or specific if the user opts in.
  22. Marker signal countdown - During convergence event, bot's status updates with the countdown.
  Pinned message in #bridge counts down to the moment.
  23. Puzzle hint channel - Read-only #recovered-logs where the bot cross-posts significant discoveries.
   Fuels the community meta-puzzle.
  24. Convergence event live thread - When the event starts, bot opens a thread and posts sync markers
  so people can experience it together in text form too.
  
  Community / themed extras

  25. Ishimura Bugle - Weekly digest posted to #announcements: top crew activity, new media, upcoming
  events, upcoming maintenance. Auto-generated from Stats.
  26. Kyne AI chatbot - Small LLM-backed bot (Ollama on ishimura) that answers questions in-character as
   Dr. Kyne. Knows the Ishimura ecosystem: "Where do I find the mods?" gets a themed but useful reply.
  Fun replacement for a support FAQ.
  27. CEC intercom soundbytes - Bot rarely (once a day-ish) posts one of a curated set of audio clips
  into voice channels - "Attention crew, hydroponics cycle complete." Just flavor.
  28. Marker whispers - Bot's daily status is a rotating cryptic quote from the audio-log corpus. Free
  lore infusion.
  29. Necromorph hunt sightings - When someone clicks an ARG glyph on the site, bot announces the
  sector. Ties the physical-feeling ARG into text chat.
  30. Achievement showcase - Auto-posts when someone hits a milestone. @user just recovered their 25th 
  audio log - promoted to Rating 3.

  Server structure suggestion
  
  Text channels:
  - #bridge - main chat
  - #ship-log - auto-generated events
  - #new-arrivals - media additions
  - #requests - fulfilled + open
  - #recovered-logs - ARG announcements
  - #hangar-status - game server pings
  - #bugle - weekly newsletter
  - #tech-support - infra questions (Kyne AI helps first)
  - #crew-quarters - off-topic
  - #suggestions - anonymous suggestion box mirror
  - #admin (private) - ops
  - #recovered-logs-hints (opt-in) - puzzle spoilers

  Voice channels:
  - 🚨 Bridge
  - ⚕️ Medical Bay
  - 🔧 Engineering
  - 📦 Cargo Bay
  - Dynamic game rooms (auto-created)
  
  Roles hierarchy:
  - Captain (owner)
  - Bridge Officer (admins)
  - Engineering (moderators)
  - Position roles (Security, Medical, Miner, Science, Recreation) - cosmetic
  - Crew (verified voidauth users)
  - Passenger (unverified visitors)

  Bot architecture
  
  Single Python service (comms) on ishimura:
  - discord.py + Flask combo (Flask for webhooks from your other services calling POST /event)
  - SQLite for user ↔ discord ID mapping
  - Uses your existing sops keys for Jellyfin/Navidrome/Hangar/Refinery API access
  - New nix module modules/nixos/ishimura/comms.nix matching your other Flask services
  - ~4-6 evenings for the core, then incrementally add commands/integrations
  
  If I had to pick three killer bots to ship first
  
  - Comms Officer with /link + Ship's Log auto-poster - makes Discord feel connected to the ship without
   any user having to do anything
  - /request + /now-playing - highest value slash commands, replaces "hey what's up with X?"
  back-and-forth
  - Dynamic game voice rooms - creates natural gathering points when people are playing, without manual
  coordination

  Want to sketch the comms bot as a design spec?
