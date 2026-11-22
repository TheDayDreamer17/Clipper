#!/usr/bin/env python3
"""
Reset Cache & Database Utility for Clipper
- Wipes old rendered clips from output/training_candidates and output/tournament_winners
- Cleans downloaded ring buffer chunks and vision cache
- Cleans generated brand overlay frames
- Reinitializes a clean, empty telemetry.db schema
"""
import os
import shutil
import sqlite3
from pathlib import Path

def reset_all():
    root = Path(__file__).parent.parent
    
    # 1. Directories to clean
    dirs_to_clean = [
        root / "output/training_candidates",
        root / "output/tournament_winners",
        root / "downloads/ring_buffer",
        root / "downloads/vision_temp",
        root / "data/brand_assets"
    ]
    
    deleted_files = 0
    for d in dirs_to_clean:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    f.unlink()
                    deleted_files += 1
                elif f.is_dir():
                    shutil.rmtree(f, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        
    print(f"🧹 Cleaned {deleted_files} old clip files and cached assets across output & downloads.")

    # 2. Reset Database: data/telemetry.db
    db_path = root / "data/telemetry.db"
    if db_path.exists():
        db_path.unlink()
        print("🗑️ Removed old data/telemetry.db")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # Recreate clean tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS stream_sessions (
            session_id TEXT PRIMARY KEY,
            creator_name TEXT,
            platform TEXT,
            stream_url TEXT,
            language TEXT,
            started_at REAL,
            status TEXT
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS frame_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            streamer TEXT,
            timestamp REAL,
            decision TEXT,
            confidence REAL,
            event_type TEXT,
            reason TEXT,
            created_at TEXT
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tournament_events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT,
            creator_name TEXT,
            event_type TEXT,
            timestamp_window TEXT,
            winner_candidate TEXT,
            virality_score REAL,
            quality_tier TEXT,
            veracity_passed INTEGER,
            hook_velocity REAL,
            output_path TEXT,
            rejection_notes TEXT,
            created_at REAL
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_live_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            agent_name TEXT,
            event_type TEXT,
            message TEXT,
            details_json TEXT,
            timestamp TEXT,
            created_at REAL
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS training_clip_ratings (
            clip_id TEXT PRIMARY KEY,
            video_path TEXT,
            target_search TEXT,
            category TEXT,
            language TEXT,
            channel TEXT,
            creator TEXT,
            expected_spoken TEXT,
            expected_vision TEXT,
            duration REAL,
            virality_score REAL DEFAULT 0.0,
            human_stars INTEGER,
            human_verdict TEXT,
            human_critique TEXT,
            rated_at REAL
        );
    """)

    conn.commit()
    conn.close()
    print("✨ Initialized fresh, empty schema in data/telemetry.db")

if __name__ == "__main__":
    reset_all()
