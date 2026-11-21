# Clipper Persistent Workspace Context & Architecture

This rule file ensures that any agent session operating within this repository inherits the full context of the project architecture, live daemons, database states, and active training loops.

For the complete project briefing and live memory map, refer to [AGENTS.md](../../AGENTS.md).

### Quick Reference:
- **Web UI & Control Center**: [http://localhost:3000](http://localhost:3000) (`src/web_ui.py`)
- **Database**: `data/telemetry.db` (SQLite WAL mode)
- **100 Training Cuts**: `output/training_candidates/clip_001.mp4` through `clip_100.mp4`
- **Dual Catalogs**: `data/properties_english.json` and `data/properties_hindi.json`
- **Deduplication Matrix**: `data/event_matrix.json` (`is_event_duplicate`)
- **Active Learning**: `src/self_learner.py`
- **Master Skill**: `.agent/skills/autonomous-stream-clipper/SKILL.md`
