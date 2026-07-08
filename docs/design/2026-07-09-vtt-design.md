# USG Ishimura VTT - D&D Virtual Tabletop Design (`vtt.ishimura.lol`)

**Status:** design absorbed from notes/memory/project_vtt.md on 2026-07-09. Backlog project - do NOT start until games hub is ~80% complete. Targeting **Foundry VTT feature parity** with Dead Space theming and deep integration with the ishimura ecosystem.

**One-liner:** Self-hosted virtual tabletop for D&D 5e that matches the ishimura Flask + SocketIO stack. Bakes in only what we use, shares login/tickets/avatars with the rest of the site, and integrates with stats + achievements + music (navidrome successor).

## Why not Foundry

- $50 license per user (world-share works with one but still a cost)
- Node.js stack diverges from ishimura's Python/Flask fleet
- Theming is layered but not deep - matching ship aesthetic requires CSS overrides that break on version updates
- Module ecosystem is powerful but overwhelming; own build lets us bake in only what we use
- Small friend group means "just enough" beats "everything possible"

## Why DIY is defensible

- Same reason chess/games hub/refinery/requests exist as custom builds: fits ishimura theming, lives on same VoidAuth/Pangolin/systemd/sops fabric, integrates with stats/achievements/tickets
- One shared login covers rec deck + VTT + stats + everything else
- Deep integration: dice engine from `games/dice_bp.py`, character avatars from dicebear customizer, ambient music from navidrome/successor via Subsonic API, achievement events via stats webhook

## Guiding principles

- **Not multi-system.** 5e (SRD via open5e) only. Sheet renderer + rules engine stay 5e-shaped.
- **No plugin/module ecosystem.** If we want a feature, we build it in-tree.
- **Web UI works on tablet but no native mobile apps.**
- **Discord for voice.** No WebRTC voice chat.
- **Human-curated content only.** No AI-generated content.

## Tiered feature roadmap

Foundry has ~15 years of development so parity is multi-phase. Each tier is a distinct shippable milestone.

### Tier 0 - Foundation

Prereq for anything else.

- VoidAuth SSO
- Campaign / world container (top-level persistent world per group)
- Session (a play instance within a campaign)
- Roles per campaign: GM, player, spectator
- Real-time sync via SocketIO namespace per campaign
- Persistent state in SQLite at `/persist/vtt/vtt.db`

### Tier 1 - Core VTT MVP (playable game)

Minimum to run an actual D&D session.

- Scene canvas with hex or square grid, GM uploads map image
- Tokens - drag/drop, snap to grid, movement, per-token owner
- Turn tracker / initiative - GM builds encounter order, next-turn button, current-turn highlight
- Text chat - IC/OOC toggle, whisper, roll results appear inline
- Dice roller - formula parser (see below)
- Basic character info - name, portrait, HP, AC, initiative bonus
- GM view vs player view - GM sees all tokens, players see own + revealed
- Ping/point - alt-click to draw attention

**Dice formula parser must handle:**

- `1d20+5`, `3d6+2` - basic
- `2d20kh1` (advantage), `2d20kl1` (disadvantage)
- `3d6!` (exploding on max), `4d6dl1` (drop lowest - ability score gen)
- `3d6r1` (reroll 1s), `3d6r<3` (reroll <= 3)
- Multi: `1d20+5 + 2d6+3`
- Named: `/r 1d20+5 "Sword attack"`
- Inspiration: [rpg-dice-roller](https://github.com/GreenImp/rpg-dice-roller). Basic dice code already in `games/dice_bp.py`.

### Tier 2 - Character sheets + compendium

Makes VTT actually useful vs a shared whiteboard.

- D&D 5e character sheet - tabbed (attributes, skills, equipment, spells, features, biography)
- Compendium - shared library of spells, monsters, items, races, classes, backgrounds, feats
  - Backend: [open5e API](https://open5e.com/) as source of truth for SRD content, mirror to local SQLite on first import
  - User-uploaded homebrew per campaign
- [5e-tools](https://5e.tools/) mirror at `5etools.ishimura.lol` for offline lookup, linked from VTT sidebar
- Character import - JSON from open5e format, D&D Beyond exports (legal-check), Foundry actor exports
- Sheet-driven rolls - click Shortsword auto-rolls attack + damage, click Save vs Con → 1d20+conmod, whisper to GM

**Legal note:** open5e = SRD content only, safe. 5e-tools = grey area (scrapes WotC content). Self-hosting for personal use defensible; do NOT expose 5e-tools publicly.

### Tier 3 - Combat + mechanics

Full-parity combat handling.

- Combat tracker - init order, HP bars, status conditions per token, damage/healing prompts
- Status effects - concentration, prone, stunned, poisoned. Icons on tokens
- Damage/healing application - GM drags roll result onto token, HP updates
- Death saves - auto-track successes/failures, notify at 3
- Concentration - auto-prompt Con save when damaged while concentrating
- Advantage/disadvantage system-wide (right-click roll → adv/normal/dis)
- Attack workflow - to-hit vs target AC, damage roll, apply damage - one-click sequence
- Saving throw prompts - GM broadcasts "everyone save vs Dex DC 15" → each player gets Roll Save button
- Group rolls - GM requests "everyone roll perception", sees all results in chat

### Tier 4 - Vision, fog, lighting

Where Foundry really shines. Big scope.

- Fog of war - GM reveals areas as party moves
- Line of sight vision - tokens with vision only see within sight range through walls
- Wall placement - GM draws walls on scene, walls block vision + movement
- Vision types - normal, darkvision (60/120ft), blindsight, truesight
- Dynamic lighting - torches/lanterns emit light within radius, dim vs bright zones
- Global illumination - day/dusk/night modes for whole scene
- Vision from token - each player sees only what their token can see (heavy - needs efficient visibility mesh calculation)

**Rendering:** raw Canvas won't cut it for smooth wall/vision. Use [Pixi.js](https://pixijs.com/) - handles thousands of tokens + dynamic lighting well and matches Foundry's own choice.

### Tier 5 - Media + journaling

Atmosphere, notes, handouts.

- Journal entries - GM-controlled notes, per-campaign markdown, some public/some private
- Handouts - GM shows image/text to players
- Image share - drop image in chat, everyone sees
- Music/ambient - playlist per scene. Integrate with navidrome successor's Subsonic API. GM picks track, plays for whole party. Volume mix (music/ambient/SFX separate channels)
- Sound effects one-shots - GM triggers "sword clash", plays for all
- Weather effects - snow, rain, fog overlay on scene canvas
- Scene transitions - fade to black + scene name reveal when GM switches scenes

### Tier 6 - Automation

Making common actions one-click.

- Spell effect templates - "Fireball 20ft radius" auto-draws AoE, catches targets, prompts saves
- Attack automation with modifiers, criticals, resistances
- Saving throw automation triggered by spell effects
- Concentration tracking - auto Con save when damaged
- Death save automation - roll on turn, auto-track
- Rest workflows - short/long rest handles HD spending, spell slot refresh, exhaustion
- Encounter builder - drag monsters from compendium, calculate CR + XP, save as template

### Tier 7 - Import / interop

Getting content in without retyping.

- Foundry world import - parse `.zip` world exports, reconstruct scenes/actors/journal
- D&D Beyond character import - via API or JSON export (legal-check)
- Roll20 export import - .json parser
- PDF import (aspirational) - parse stat block from PDF into monster entry
- Actor/item JSON drag-drop from open5e or 5e-tools directly

### Tier 8 - Extras / aspirational

- Drawings / annotations on scene
- Notes on map (clickable pins revealing journal entries)
- Random tables - custom d100 (weather, encounters, loot)
- Loot generator - drag treasure hoard by CR → auto-generates coins/gems/items
- Party inventory - shared bag
- Session log auto-generation - export chat + rolls + key moments as markdown
- Encounter difficulty calculator vs party level
- Wildshape / polymorph - swap character sheet temporarily
- Custom system support - not just 5e. PF2, Blades in the Dark (huge scope, defer/skip)

## Stack decisions

- **Backend:** Flask + Flask-SocketIO with `threading` async mode (same as chess/duckrace/connect4). Namespace per campaign.
- **Frontend:** vanilla JS + [Pixi.js](https://pixijs.com/) for scene canvas (walls, vision, tokens, dynamic lighting). Vue or Alpine.js for character sheets if reactivity gets painful.
- **Persistence:** SQLite at `/persist/vtt/vtt.db`.
- **Media storage:** `/persist/vtt/media/` for uploaded maps + portraits, served via nginx sidecar or Traefik file middleware (avoid Flask serving big images).
- **Auth:** VoidAuth SSO, Remote-User header pattern.
- **Real-time:** SocketIO namespace `/vtt/campaign/<id>`.
- **URL:** `vtt.ishimura.lol` via Pangolin route (same voidauth-forwardauth pattern as chess).

## Data model sketch

```
users (id, username, chips, ...)  -- shared with rec deck
campaigns (id, name, gm_user, created_at, settings_json)
campaign_members (campaign_id, user_id, role)
scenes (id, campaign_id, name, map_url, grid_size, grid_type, walls_json, lights_json)
tokens (id, scene_id, owner_user_id, character_id?, x, y, image_url, hp_current, hp_max, ...)
characters (id, campaign_id, owner_user_id, name, portrait_url, sheet_json)
combats (id, scene_id, round, active_token_id, initiative_json, started_at)
combat_effects (id, combat_id, token_id, effect_key, duration_rounds, remaining)
chat_messages (id, campaign_id, session_id, user_id, kind, body, roll_json, whispered_to, created_at)
journal_entries (id, campaign_id, name, body_markdown, folder, permissions_json, created_at)
handouts (id, campaign_id, name, image_url, revealed_to_json, created_at)
compendium_entries (id, source, kind, name, data_json)
random_tables (id, campaign_id, name, entries_json)
```

## Integration points

- **Stats/achievements** - VTT emits events to `stats/webhook/games` with `source="vtt"`:
  - `session_start`, `session_end` with duration
  - `character_created`, `character_leveled`
  - `combat_won`, `character_died`
  - `critical_hit`, `critical_fail` (streak achievements)
  - Total sessions run counts toward "regular player" achievement
- **Rec deck** - shared users table, shared tickets. Optional: tickets ↔ in-game gold conversion. Nav link both ways.
- **Music** - VTT playlist system consumes navidrome successor's Subsonic API to pull tracks.
- **Dicebear avatars** - character portraits default to user's ishimura avatar.
- **Discord bot** - session-start notification, session-end summary.
- **Stats page** - "sessions played", "characters killed", "highest damage roll" etc.

## Standalone vs part of rec deck

**Standalone at `vtt.ishimura.lol`** but with shared user/ticket infrastructure.

Reasons:

- Session length is fundamentally different (hours vs minutes)
- Screen layout differs sharply (VTT = full-canvas immersive; rec deck = tile grid)
- GM tooling adds complexity that doesn't belong in a games hub
- Two separate mental spaces for two separate activities

Keep them linked: same VoidAuth login, same tickets, shared avatar, nav bar links, stats aggregates from both.

## Realistic build order + estimates

- **Tier 0 + Tier 1**: 2-3 focused sessions (~2000-3000 lines). Playable-if-basic VTT.
- **Tier 2**: 3-4 sessions (~3000 lines). Character sheets are content-heavy; open5e integration is careful work.
- **Tier 3**: 2-3 sessions (~1500 lines). Combat tracker + status effects + damage flow.
- **Tier 4**: 4-6 sessions (~2500 lines). Vision/lighting is genuinely hard - Pixi.js + shadow calculations.
- **Tier 5**: 2-3 sessions (~1500 lines). Journal + audio + handouts.
- **Tier 6+**: incremental as we use it.

Rough total for Tier 1-5 (genuinely usable D&D VTT): ~10-15 focused sessions, ~10-12k lines. Big project.

## How to apply

- Do NOT start until games hub is at ~80% (poker + a couple more core games shipped).
- When starting, spec Tier 1 explicitly first, ship it, run one real D&D session with the crew, gather friction, then plan Tier 2.
- Never try to build Foundry parity in one push - iterate tier by tier.
- 5e-tools mirror: build separately as a `5etools.ishimura.lol` static container, keep it tailnet-only for legal safety.

## Ties into

- [[games hub]] - shared users/tickets, must be ~80% done first
- [[stats-extension]] - VTT emits events for achievements
- [[fretboard-successor]] - navidrome replacement provides music via Subsonic API
- [[comms officer]] - Discord bot posts session start/end
