# boot.asteroid Sandbox Architecture Plan

## Purpose
This document defines long-term architecture direction for `boot.asteroid`.
It is a guidance framework for incremental development, not a single milestone implementation.

Primary objective: evolve the game into a compact systemic space sandbox where each mechanic strengthens one shared gameplay loop.

## Core Loop
`explore -> scan -> discover -> trade/contract -> earn resources -> upgrade/build -> claim/expand -> defend -> explore further`

All feature decisions should answer: "Which step(s) of the loop does this improve?"

## Architectural Principles
1. Keep each system simple in isolation.
2. Require cross-system interaction: every new feature must meaningfully touch at least two existing systems.
3. Prefer deterministic simulation over persistent heavy state when equivalent gameplay value is possible.
4. Keep the resource model small and legible.
5. Prefer visual communication over text-heavy UI.
6. Preserve pacing and readability suitable for desktop now and potential mobile targets later.

## Unified Planet Model
All planets follow one ruleset.

Rules:
1. Every planet is a settlement planet.
2. Every planet accepts exactly one metal type.
3. Planet metal type is encoded by cloud color.
4. That same color identity appears in world sprite, minimap marker, cargo iconography, and contracts/UI.

Design intent:
- Players should identify planet type from minimap alone.
- Planet interaction should not require opening detailed panels for basic routing choices.

## Lightweight Settlement Simulation
Per-planet tracked values:
- population
- food
- water
- power
- security
- happiness

Happiness model:
- Derived from normalized fulfillment of key needs (`supply / requirement` style computation).
- Used as a multiplier/weight, not as a separate micromanagement subsystem.

Happiness affects:
- production efficiency
- contract payout quality
- settlement growth rate
- raid pressure probability

Guardrail:
- Avoid adding citizen-level simulation, job classes, or chain dependencies unless required for core-loop clarity.

## Sector Resource Networks
Owned sectors that are adjacent and uninterrupted form a shared logistics region.

Network behavior:
- Shared pool access for selected essentials and commodities.
- No manual ship-by-ship hauling requirement for baseline operation.
- Regional specialization is encouraged (not all planets must self-supply every need).

Candidate shared categories:
- food
- water
- power
- medical supplies
- commodities

## Infrastructure and Buildables
Buildables should provide clear loop leverage and defense value.

Priority structure families:
1. Medical facilities
2. Security stations
3. Factories
4. Trade hubs
5. Mining drone platforms

Reference special case:
- Null-sec mining station in asteroid sectors deploys autonomous drones for passive extraction.
- Benefit is intentionally paired with defense obligations to create strategic risk/reward.

## Sector Control and Conflict
Sector ownership should be earned through visible, staged conflict.

Claim sequence:
1. Remove defending forces.
2. Begin claim process.
3. Survive reinforcement waves.
4. Claim completes only if player remains alive in-sector.

Presentation rule:
- Reinforcement fleets must enter from sector edges.
- No direct on-screen enemy pop-in spawning.

Post-claim pressure:
- Owned sectors can receive raids.
- Security infrastructure reduces raid risk/severity.

## Scanner and World Sampling
Scanner should expose information without becoming a heavy persistent map database.

Rules:
1. Scanner reveals nearby world entities and pressure signals (planets, stations, asteroid fields, enemy pressure, anomalies).
2. Data is produced from deterministic seed + coordinates.
3. Scanner output is a temporary snapshot, not full permanent world-state storage.

Benefits:
- Lower memory footprint.
- Reproducible exploration outcomes.
- Cleaner architecture for large-space traversal.

## Anomalies and Environmental Hazards
Anomalies deepen exploration and serve as soft progression gates.

Examples:
- black holes (engine pressure)
- radiation stars (shield pressure)
- nebula interference (sensor pressure)

Gating model:
- Access is technically possible before upgrades.
- Survival/reliability improves strongly with upgrades.
- Avoid hard-lock walls unless needed for tutorial or critical sequence integrity.

## Scope Control Rules
1. Do not introduce a new standalone subsystem when extending an existing one is sufficient.
2. Do not add new resource types without removing or consolidating existing ones.
3. Avoid adding menu depth that slows session flow.
4. Favor readable map-level affordances first, panel complexity second.
5. Gate implementation by loop value, not feature novelty.

## Incremental Delivery Roadmap
### Phase 1: Readability and Identity
Goal: improve player recognition speed and decision clarity.

Deliverables:
1. Unified metal color identity across planet visuals, minimap markers, cargo UI, and contract labels.
2. Single-acceptance metal rule enforcement on settlement planets.
3. Basic scanner snapshot consistency pass for entity readability.

Exit criteria:
- Player can route to target metal planets from minimap without opening per-planet detail panels.

### Phase 2: Settlement and Economy Coherence
Goal: make settlements matter without introducing management overhead.

Deliverables:
1. Lightweight settlement stat model integration.
2. Happiness-derived modifiers for output, payouts, growth, and raid risk.
3. Adjacent-sector shared resource network baseline behavior.

Exit criteria:
- Strategic value emerges from where player owns space, not only what they individually mine.

### Phase 3: Territorial Risk/Reward
Goal: establish defendable ownership loop and passive-economy stakes.

Deliverables:
1. Multi-stage sector claim flow with reinforcement waves.
2. Edge-entry reinforcement spawning for immersion consistency.
3. Initial security and mining infrastructure with clear trade-offs.

Exit criteria:
- Expansion creates both income opportunity and defend obligations.

### Phase 4: Exploration Pressure Layer
Goal: turn travel and scanning into meaningful progression pressure.

Deliverables:
1. Seed-sampled anomaly/hazard layer surfaced by scanner.
2. Upgrade-linked survivability scaling in hazard zones.
3. Contract/discovery hooks that motivate risk-managed exploration.

Exit criteria:
- Upgrades materially broaden viable exploration envelope.

## Feature Acceptance Checklist
Before implementing any new feature, confirm all checks:
1. It strengthens at least one explicit step of the core loop.
2. It integrates with at least two existing systems.
3. It preserves visual readability at map scale.
4. It does not force deep micromanagement.
5. It does not materially expand the resource taxonomy.
6. It can be shipped incrementally with observable player value.

## Working Agreement
- This plan is authoritative for direction, flexible for sequencing.
- Prefer small, testable slices over broad unfinished drops.
- If a proposed feature conflicts with this document, reduce scope or redesign before implementation.
