# 🎬 Project Clipper: AI-Powered Gaming Stream Clipper & Short Generator

> High-velocity, zero-token, local-first streaming clipper designed for major gaming launches (GTA 6, GTA 5). Runs natively on Apple Silicon Metal GPU with bilingual Hinglish/Hindi topic detection.

---

## ⚡ Key Capabilities

* **Multi-Platform Stream Discovery:** Auto-fetches top performing live streams from **Twitch** (via public GraphQL API, sorted by live viewer count) and **YouTube** without consuming Google Cloud Data API quotas.
* **Audio-First Streaming Architecture:** Extracts and analyzes lightweight audio streams in RAM (~1 MB/min) instead of downloading heavy full-video files. Video is only retrieved when a high-confidence topic match is triggered.
* **100% Local Inference (Zero Cloud Tokens):**
  * **Speech-to-Text:** Powered by `mlx-whisper` on Apple Silicon Metal GPU (~15x to 30x real-time factor).
  * **Topic Matching:** Dual-layer bilingual keyword ontology covering English, Hindi Devanagari, and Romanized Hinglish slang.
* **20 Pre-Built Launch Content Buckets:** Pre-mapped to top search queries (opening intro, graphics first look, police AI, vehicle stunts, fails, easter eggs, radio stations).
* **Automated 9:16 Vertical Video Production:** Slices highlight windows, applies normalized audio timestamps (`make_zero` PTS sync), and formats to 1080x1920 vertical video with blurred background gameplay framing.

---

## 🏗️ Architecture

```mermaid
flowchart LR
    A["Twitch / YouTube Live Stream"] --> B["Audio Stream Buffer (~1 MB/min)"]
    B --> C["mlx-whisper (Metal GPU)"]
    C --> D["Bilingual Topic Matcher (20 Buckets)"]
    D -->|"Topic Hit Found"| E["FFmpeg Precision Slicer (-5s to +20s)"]
    E --> F["9:16 Vertical Video (1080x1920 MP4)"]
```

---

## 🚀 Quick Start

### 1. Prerequisites
* macOS with Apple Silicon (M1/M2/M3/M4/M5/M6)
* [Homebrew](https://brew.sh)
* FFmpeg (`brew install ffmpeg`)

### 2. Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd Clipper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install yt-dlp mlx-whisper requests
```

### 3. Usage

#### Run the End-to-End Pipeline
```bash
# Auto-fetch best performing Hindi GTA stream and generate a Short
python pipeline.py --query "GTA 5 Hindi"

# Or process a direct stream/video URL
python pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

#### Discover Live Streams
```bash
# Search Twitch top GTA live streams
python src/fetcher.py --platform twitch

# Search YouTube top GTA streams
python src/fetcher.py --platform youtube --query "GTA 5 Hindi"
```

---

## 📁 Repository Structure

```
Clipper/
├── config/
│   └── topics.json         # 20 pre-built content buckets with bilingual keywords
├── src/
│   ├── fetcher.py          # Twitch GQL + YouTube discovery engine
│   ├── ingest.py           # Audio-first stream extractor
│   ├── matcher.py          # Bilingual Hinglish/Hindi topic scanner
│   ├── slicer.py           # FFmpeg 9:16 vertical video formatter
│   └── transcribe.py       # MLX Whisper Metal GPU wrapper
├── pipeline.py             # Main end-to-end orchestration entrypoint
├── .gitignore
└── README.md
```

---

## 📜 License
MIT
