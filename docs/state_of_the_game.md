# state_of_the_game

## Purpose
This file is the canonical living design document for `boot.asteroid`.

Use this as the source of truth between sessions.
Update it after meaningful implementation passes.
Do not treat it as a chronological session log.

When an idea is completed, move it into the relevant "Current State" section below.

## Between-Pass Rule
For every implementation pass, do this before ending the pass:
1. Check this document for drift vs current code state.
2. Update "Current State" with completed behavior.
3. Update "Active TODO Queue" with next concrete slices.
4. Remove TODOs that are now complete by folding them into "Current State".

## Working Procedure
Use this operating procedure on every pass:
1. Read `state_of_the_game.md` first.
2. Pick one small, shippable slice from `Active TODO Queue`.
3. Implement with keyboard/mouse compatibility preserved while improving touch-forward behavior where applicable.
4. Verify changed files for errors.
5. Update this document:
	- move completed work into `Current State`
	- refresh `Active TODO Queue`
	- keep `Future Implementation Fronts` aligned with current priorities

## Core Loop
`explore -> scan -> discover -> trade/contract -> earn resources -> upgrade/build -> claim/expand -> defend -> explore further`

All systems should reinforce this loop.

## Design Constraints
1. Keep systems simple in isolation.
2. Every new system must connect to at least two existing systems.
3. Keep resource taxonomy small.
4. Prefer visual communication over text-heavy UI.
5. Keep flow smooth and mobile-friendly where practical.
6. Ship in small slices; avoid broad rewrites.

## Current State
### Planets and Visual Identity
- Every planet is a settlement planet with a single accepted metal.
- Settlement planets now explicitly exclude `gold` as an accepted market metal; gold remains upgrade currency while planets trade other metals.
- Metal identity is color-signaled across:
	- planet sprites (including cloud tint)
	- minimap sector thumbnails
	- cargo inventory rows
	- planet trade and contract market labels

### Settlement and Economy
- Per-planet lightweight settlement model exists with:
	- population, food, water, power, security, happiness
- Happiness affects:
	- planet contract payouts
	- market sale multipliers
	- settlement growth/decline over time
	- raid targeting pressure
- Adjacent uninterrupted owned sectors share pooled essentials:
	- food, water, power, medical, parts

### Territory and Defense
- Claim flow is staged:
	- clear defenders -> start claim -> survive timed waves -> complete claim
- Claim and raid reinforcements enter from sector edges.
- Claim HUD includes next-wave countdown and edge-entry telegraphing.
- Initial defense infrastructure is active:
	- station upgrades contribute to sector security
	- sector security dampens raid wave size/intensity
	- station infrastructure categories are now upgradeable:
		- mining drones (passive economy)
		- interceptor drones
		- turret grid
		- shield net
	- infrastructure modules now have distinct world-space silhouettes/animation for at-a-glance combat readability.
	- shield net now provides module damage mitigation and gradual infrastructure regeneration.
	- interceptor drones can now probabilistically intercept incoming hostile shots near defended stations.
	- mining drones now feed both credits and shared `parts` resource output into the sector economy network.
	- dedicated mining platforms are now deployable from the Build tab as a separate defendable buildable (not a station-upgrade level).
	- mining platforms render in world space with health bars and contribute passive credits + `parts` while alive.
	- raids and hostile station fire now prioritize mining platforms in raided sectors before other defensive structures.
	- mining platform logistics links now degrade to offline during raids; offline platforms buffer output instead of paying immediately.
	- flying close to offline platforms restores route links and automatically recovers buffered credits/parts.
	- Build tab and HUD now display platform link status and buffered cargo to keep recovery pressure readable.
	- periodic convoy retrieval windows now create escort-style logistics pressure for platform routes.
	- missed convoy windows, especially during raids, now reduce buffered recovery efficiency until routes are restabilized.
	- escorting/stabilizing active convoy windows improves route efficiency; Build tab and HUD now surface convoy timers/progress/efficiency.
	- repeated missed convoy windows now build logistics strain that temporarily suppresses passive platform output until a successful stabilization clears the failure chain.
	- sectors under convoy strain are now weighted for higher raid pressure against platform logistics.
	- HUD and Build tab now expose convoy strain alongside efficiency/timers to keep consequence state readable.
	- convoy strain now escalates raid intensity directly: strained sectors can receive larger/faster raid waves and extra wave count pressure.
	- convoy warning levels (`STABLE`/`ELEVATED`/`HIGH`/`CRITICAL`) are now surfaced in HUD and Build logistics status.
	- map snapshots now include mining platform markers for sector-level visibility.
	- enemy fire can target player infrastructure modules directly in low-security combat zones.
	- player-built stations, mining platforms, and standalone defense turrets now use manual click-to-place placement flow from the Build tab instead of auto-dropping.
	- placement enforces edge exclusion and buildable separation rules so new structures cannot be dropped on sector borders or on top of major sites.
	- mining platforms now dispatch visible drones across the whole active sector to any live asteroid, harvest drifting targets, and convert mined output into credits plus shared `parts`.
	- standalone defense turrets now alternate between two space-combat variants:
		- `onslaught_alpha`: fast twin-shot anti-fighter pattern
		- `onslaught_barrage`: heavier multi-barrel burst pattern
	- standalone turret and mining-platform silhouettes are now rendered directly in world space so placed structures remain readable during live combat and map review.

### Scanner and Anomalies
- Scanner uses deterministic seed + coordinates for repeatable snapshots.
- Scanner intel includes:
	- planets, stations, asteroids, enemy pressure, anomalies
- Map thumbnails render anomaly markers for:
	- black holes
	- radiation stars
	- nebula interference
- Active-sector anomaly effects are soft-gated by upgrades:
	- black hole pressure -> engine tuning mitigates
	- radiation pressure -> shield level mitigates
	- nebula interference -> scanner level mitigates
- Scanner visibility contract now separates persistent map knowledge from tactical intel:
	- station/planet snapshots persist once a sector is explored/scanned
	- unit/asteroid/anomaly tactical intel is shown only inside a live-scan visibility window
	- scanner capstone passive ping refreshes current-sector tactical intel only
	- remote scan clicks reveal only the selected adjacent sector tactically (no expanded spillover)
	- tactical visibility expires on timer and clears on sector transition

### Contracts and Risk/Reward
- Contract generation now applies anomaly-linked incentives for anomaly-sector destinations:
	- higher payout/hazard bonus
	- elevated risk/pressure metadata
	- anomaly tag summary visible in map contract details

### Difficulty and Progression Scaling
- Difficulty profiles now differ in more than raw stats:
	- AI aggression, accuracy, strafe pressure, fire intent, tracking memory
	- enemy speed/health/view/shoot cadence
	- economy/drop/upgrade multipliers
- Aggregate player progression is represented by `Command Level` (not combat-only).
- Command Level is displayed in HUD and the `I` ship systems panel.
- Enemy pressure scales with contract pressure and Command Level.
- Threat and pressure growth are now difficulty-configurable via per-profile curve knobs:
	- `command_threat_step`
	- `command_threat_max`
	- `pressure_cap`
- Enemy contact composition is now difficulty-tuned (easy suppresses tank spikes, hard promotes heavier pressure roles).
- Hard tank conversion rates were revalidated and trimmed (harasser->tank 16%, bomber->tank 5%) to reduce early-wave tank clustering.
- Pause/menu difficulty card now displays key AI multipliers for rapid tuning verification.
- Difficulty verification sweep has been run against low/mid/high Command Levels to smooth hard-mode early spikes while preserving hard-mode identity.
- Enemy contact faction metadata is now normalized during persistent-pack hydration and enemy sync fallback creation, so contact visuals/behavior remain aligned with sector/raid claim context.

### Touch-Forward Controls
- Optional on-screen action controls are now available during live flight for:
	- fire
	- interact
	- map
	- pause
- Optional on-screen movement controls are now available during live flight via a touch D-pad:
	- rotate left/right
	- thrust forward/reverse
- Touch actions preserve keyboard/mouse parity by routing into existing key-driven gameplay behavior.
- Touch D-pad latching now re-evaluates per frame from tracked pointer positions (with small hit-margin expansion), improving rotate/thrust/reverse reliability for hold and drag-into-pad gestures.
- D-pad direction resolution is now deterministic under overlap/edge cases:
	- when expanded hitboxes overlap, nearest directional center wins
	- when inside the overall D-pad bounds but between buttons, dominant-axis fallback selects a direction
- Touchscreen finger events now convert normalized `FINGER*` coordinates using the active display surface size (not static constants), improving touch-to-button alignment on real hardware/window scales.
- Touch D-pad input now drops direction immediately on explicit finger/mouse release, while keeping only a very short jitter-grace window for transient event gaps during active holds.
- Docked and pause/menu overlays now use larger touch targets for key actions:
	- contract deliver/accept
	- station infrastructure upgrades
	- undock/take off
	- controls/audio/map pause-menu actions

### Pause Menu and Tabs
- Pause is now both keyboard and clickable/touchable via the top-right `Esc: Pause` button.
- Player-facing pause flows are tab-driven inside one pause shell:
	- Home
	- Map
	- Ship
	- Build
	- Controls
	- Audio
- Hotkeys jump directly to tabs while paused/playing:
	- `M` map
	- `I` ship
	- `B` build
- Controls tab is now grouped for faster scanning:
	- Flight
	- Combat
	- Menus and Tabs
	- Touch and Parity
	- Dev
- Controls wording now explicitly calls out keyboard/mouse/touch parity to reduce input-mode ambiguity.
- Shared UI theme now uses a darker gray/black baseline with white/red emphasis to reduce pastel-heavy presentation.
- Docked station panel now uses category tabs + sub-tabs with one active content pane at a time:
	- Ship -> Combat Fit / Utility Fit
	- Station -> Defense Grid / Infrastructure
	- Contracts -> dedicated mission board pane
- Build pause panel now uses category tabs + sub-tabs with focused panes:
	- Construction -> Core / Sites
	- Infrastructure -> Economy / Defense
	- Logistics -> Links / Convoys
- Build and station tab clicks are fully wired into UI state transitions (`tab:` actions) so category switches do not require leaving the panel.
- Overlay spacing and clipping rules were normalized across station/planet/build/map panels for `1366x768` and `1920x1080` targets:
	- station dock header, owner label, and tab rows now use dynamic vertical spacing and extra margin to guarantee no overlap at runtime
	- station and planet contract panes now cap visible rows by available vertical budget
	- map side-info stack now uses cursor-based budgeted rendering instead of fixed y offsets
	- build panel now uses resolution-scaled margins/tab widths to avoid edge crowding
- Esc behavior now matches pause-menu messaging:
	- Esc from `playing` opens pause
	- Esc from `paused` resumes gameplay
	- Esc from `menu` exits game

## Balance Maintenance Policy
- Recalibrate Command Level weighting whenever new defenses, automation, ownership mechanics, or strategic systems are added.
- Rebalance difficulty AI traits when new enemy roles or movement/combat mechanics are introduced.
- Preserve difficulty identity:
	- `easy`: fewer spikes, lower behavior pressure
	- `normal`: baseline systemic pressure
	- `hard`: stronger behavioral pressure, not only health inflation

## Future Implementation Fronts
### Front A: AI/Difficulty Fine Tuning
- Validate enemy composition pressure by difficulty (especially tank frequency).
- Tune behavior multipliers against early/mid/late Command Level breakpoints.

### Front B: Defense and Infrastructure Expansion
- Add additional defendable buildables (for example mining platforms) tied to territory risk/reward.
- Ensure new buildables integrate with sector security and raid systems.

### Front C: Exploration Depth
- Extend anomaly interactions (events/rewards/failure states) while keeping soft-gate philosophy.

## Active TODO Queue
- Front B next slice:
	- priority 1: tune mining drone travel/harvest cadence and payout feel now that drones can respond sector-wide.
- Front B next slice:
	- priority 2: tune `onslaught_alpha` vs `onslaught_barrage` so the two standalone turret roles stay mechanically distinct under raid pressure.
- Front B next slice:
	- priority 3: remove remaining duplicate stale blocks in `main.py` that can still override active gameplay/render paths.

## Acceptance Gate (For Any New Feature)
1. Strengthens at least one core-loop step.
2. Touches at least two existing systems.
3. Improves or preserves map-level readability.
4. Avoids deep micromanagement overhead.
5. Does not bloat resource taxonomy.
6. Can ship incrementally with visible player value.
