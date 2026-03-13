# release_note_draft

## March 2026 gameplay and UI pass

This pass unifies the pause shell around shared top-level tabs so Pause, Map, Cargo, Status, and Build all route through the same navigation model.
Keyboard shortcuts now behave consistently across play and pause with direct tab jumps on `M`, `I`, `S`, `B`, plus `Tab` and `Shift+Tab` tab cycling.

The old overloaded ship panel has been split into two clearer surfaces:
- `I` now opens a cargo-focused inventory panel with contract dump and metal jettison actions.
- `S` now opens a dedicated status panel for ship systems, combat readouts, command level, and sector state.

Ship progression also expanded in this pass with four new upgrade lines:
- weapon amplifier
- deflector array
- missile payload
- shipboard miners

Those systems are now live in gameplay:
- deflectors absorb asteroid impacts separately from shields and regenerate over time
- missiles use guided target acquisition with payload-based damage and splash scaling
- shipboard miners deploy visible support drones and auto-harvest nearby asteroids into the cargo hold

Map travel and sector control got a meaningful usability step forward:
- owned sectors within warp range can now be selected directly from the map for FTL jumps
- map tiles now communicate scanner-pulse targets and FTL destinations with distinct highlights

Cleanup and stabilization in this batch also removed stale pause-menu plumbing, removed the dead touch flight-movement scaffolding, and deleted the unused dummy `enemy_wave.py` module.

Push-readiness note:
- a final live sweep was completed against docking, landing, pause-tab routing, build placement, and cargo/status transitions before push prep.