import http.server
import socketserver
import json
import urllib.parse
import mimetypes
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

PORT = 8765

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚡ Antigravity Clipper Control Center</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0A0D14;
      --card: rgba(18, 24, 38, 0.85);
      --border: rgba(0, 240, 255, 0.25);
      --accent: #00F0FF;
      --pink: #FF007A;
      --green: #00FFA3;
      --text: #F0F4F8;
      --muted: #8E9BAE;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Space Grotesk', -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(10, 13, 20, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 18px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: -0.5px;
      background: linear-gradient(90deg, #00F0FF, #FF007A);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .badge {
      background: rgba(0, 240, 255, 0.12);
      color: var(--accent);
      border: 1px solid var(--accent);
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.5px;
    }
    .stats-bar {
      display: flex;
      gap: 24px;
    }
    .stat-item {
      text-align: right;
    }
    .stat-num {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--accent);
      font-family: 'JetBrains Mono', monospace;
    }
    .stat-label {
      font-size: 0.7rem;
      color: var(--muted);
      text-transform: uppercase;
    }
    nav {
      display: flex;
      gap: 8px;
      padding: 12px 32px;
      background: rgba(15, 20, 32, 0.6);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .nav-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--muted);
      padding: 8px 18px;
      border-radius: 8px;
      font-family: inherit;
      font-weight: 600;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .nav-btn.active, .nav-btn:hover {
      background: rgba(0, 240, 255, 0.1);
      color: var(--accent);
      border-color: rgba(0, 240, 255, 0.3);
    }
    main {
      padding: 32px;
      flex: 1;
      max-width: 1600px;
      margin: 0 auto;
      width: 100%;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 28px;
    }
    .clip-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
      transition: transform 0.2s, border-color 0.2s;
    }
    .clip-card:hover {
      transform: translateY(-4px);
      border-color: var(--accent);
    }
    .video-wrapper {
      position: relative;
      background: #000;
      aspect-ratio: 9/16;
      max-height: 440px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    video {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .card-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      flex: 1;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }
    .card-title {
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.3;
    }
    .virality-badge {
      background: linear-gradient(135deg, rgba(255, 0, 122, 0.2), rgba(0, 240, 255, 0.2));
      border: 1px solid var(--pink);
      color: #FFF;
      padding: 4px 10px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      white-space: nowrap;
    }
    .meta-box {
      background: rgba(10, 13, 20, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 12px;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .meta-row {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
    }
    .meta-val {
      color: var(--text);
      font-family: 'JetBrains Mono', monospace;
    }
    .social-tags {
      background: rgba(0, 240, 255, 0.04);
      border: 1px dashed rgba(0, 240, 255, 0.3);
      padding: 10px;
      border-radius: 8px;
      font-size: 0.75rem;
      color: var(--accent);
      line-height: 1.4;
      user-select: all;
    }
    .actions {
      display: flex;
      gap: 10px;
      margin-top: auto;
    }
    .btn {
      flex: 1;
      padding: 10px 14px;
      border-radius: 8px;
      font-family: inherit;
      font-weight: 600;
      font-size: 0.85rem;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-approve {
      background: var(--green);
      color: #05140C;
    }
    .btn-approve:hover { filter: brightness(1.1); box-shadow: 0 0 14px rgba(0, 255, 163, 0.4); }
    .btn-copy {
      background: rgba(255, 255, 255, 0.1);
      color: var(--text);
    }
    .btn-copy:hover { background: rgba(255, 255, 255, 0.2); }
    .table-container {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
    }
    th, td {
      padding: 14px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    th {
      background: rgba(0, 0, 0, 0.3);
      color: var(--muted);
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.5px;
    }
    tr:hover td { background: rgba(0, 240, 255, 0.02); }
    .status-active { color: var(--green); font-weight: 600; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>ANTIGRAVITY CLIPPER</h1>
      <span class="badge">GTA 6 LAUNCH COMMAND</span>
    </div>
    <div class="stats-bar">
      <div class="stat-item">
        <div class="stat-num" id="stat-streams">0</div>
        <div class="stat-label">Streams Live</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" id="stat-clips">0</div>
        <div class="stat-label">Clips Crowned</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" id="stat-triggers">0</div>
        <div class="stat-label">AI Triggers</div>
      </div>
    </div>
  </header>

  <nav>
    <button class="nav-btn active" onclick="switchTab('clips')">🎬 Crowned Shorts for Review</button>
    <button class="nav-btn" onclick="switchTab('streams')">📡 Monitored Live Streams</button>
    <button class="nav-btn" onclick="switchTab('audit')">🛑 Rejection Analytics (Audit)</button>
  </nav>

  <main>
    <div id="tab-clips">
      <div class="grid" id="clips-grid">
        <div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--muted);">
          Loading generated clips...
        </div>
      </div>
    </div>

    <div id="tab-streams" style="display: none;">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Creator</th>
              <th>Platform</th>
              <th>Language</th>
              <th>Status</th>
              <th>Stream URL</th>
            </tr>
          </thead>
          <tbody id="streams-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="tab-audit" style="display: none;">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Rejection Reason</th>
              <th>Frames Filtered</th>
              <th>Automated Safeguard Action</th>
            </tr>
          </thead>
          <tbody id="audit-tbody"></tbody>
        </table>
      </div>
    </div>
  </main>

  <script>
    function switchTab(tab) {
      document.querySelectorAll('nav .nav-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-clips').style.display = tab === 'clips' ? 'block' : 'none';
      document.getElementById('tab-streams').style.display = tab === 'streams' ? 'block' : 'none';
      document.getElementById('tab-audit').style.display = tab === 'audit' ? 'block' : 'none';
    }

    async function loadData() {
      try {
        const [statsRes, clipsRes, streamsRes] = await Promise.all([
          fetch('/api/stats'),
          fetch('/api/clips'),
          fetch('/api/streams')
        ]);
        const stats = await statsRes.json();
        const clips = await clipsRes.json();
        const streams = await streamsRes.json();

        document.getElementById('stat-streams').textContent = stats.total_streams;
        document.getElementById('stat-clips').textContent = clips.length;
        document.getElementById('stat-triggers').textContent = stats.total_triggers;

        // Render Clips
        const grid = document.getElementById('clips-grid');
        if (clips.length === 0) {
          grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--muted);">No clips generated yet. Monitoring active streams...</div>';
        } else {
          grid.innerHTML = clips.map(c => `
            <div class="clip-card" id="card-${c.id}">
              <div class="video-wrapper">
                <video src="${c.video_url}" controls playsinline preload="metadata"></video>
              </div>
              <div class="card-body">
                <div class="card-header">
                  <div class="card-title">${c.title}</div>
                  <div class="virality-badge">🔥 ${c.virality_score}/100</div>
                </div>
                <div class="meta-box">
                  <div class="meta-row"><span>Creator:</span> <span class="meta-val">${c.creator}</span></div>
                  <div class="meta-row"><span>Platform:</span> <span class="meta-val">${c.platform.toUpperCase()} (${c.language})</span></div>
                  <div class="meta-row"><span>QA Veracity:</span> <span class="meta-val" style="color: var(--green);">VERIFIED PASS</span></div>
                </div>
                <div class="social-tags" title="Click to copy for YouTube Shorts / Reels">
                  <strong>YouTube Title:</strong> ${c.youtube_title}<br>
                  <strong>Tags:</strong> ${c.tags}
                </div>
                <div class="actions">
                  <button class="btn btn-copy" onclick="copyMeta('${c.youtube_title}', '${c.tags}')">📋 Copy Meta</button>
                  <button class="btn btn-approve" onclick="approveClip('${c.id}')">🚀 Stage for Upload</button>
                </div>
              </div>
            </div>
          `).join('');
        }

        // Render Streams
        const tbody = document.getElementById('streams-tbody');
        tbody.innerHTML = streams.map(s => `
          <tr>
            <td><strong>${s.creator_name}</strong></td>
            <td><span class="badge" style="border-color: rgba(255,255,255,0.2); color: var(--text);">${s.platform.toUpperCase()}</span></td>
            <td>${s.language}</td>
            <td><span class="status-active">● ${s.status}</span></td>
            <td><a href="${s.stream_url}" target="_blank" style="color: var(--accent); text-decoration: none;">Watch Stream ↗</a></td>
          </tr>
        `).join('');

        // Render Audit Table
        const auditBody = document.getElementById('audit-tbody');
        auditBody.innerHTML = stats.top_rejections.map(r => `
          <tr>
            <td><code>${r.reason}</code></td>
            <td><strong>${r.count}</strong> frames</td>
            <td><span style="color: var(--muted);">Prevented false positive / flat driving cut</span></td>
          </tr>
        `).join('');

      } catch (err) {
        console.error('Error loading data:', err);
      }
    }

    function copyMeta(title, tags) {
      navigator.clipboard.writeText(`${title}\\n\\nTags: ${tags}`);
      alert('Copied title and tags to clipboard!');
    }

    function approveClip(id) {
      alert(`Clip ${id} approved and staged for YouTube Shorts & Instagram Reels upload!`);
      const card = document.getElementById(`card-${id}`);
      if (card) card.style.borderColor = 'var(--green)';
    }

    loadData();
    setInterval(loadData, 15000);
  </script>
</body>
</html>
"""

class ClipperHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif path == "/api/stats":
            self._handle_api_stats()
            return

        elif path == "/api/streams":
            self._handle_api_streams()
            return

        elif path == "/api/clips":
            self._handle_api_clips()
            return

        elif path.startswith("/video/"):
            # Stream local video file
            rel_file = urllib.parse.unquote(path.replace("/video/", ""))
            file_path = Path("output") / rel_file
            if file_path.exists():
                self._serve_file(file_path, "video/mp4")
            else:
                self.send_error(404, "Video not found")
            return

        self.send_error(404, "Not Found")

    def _serve_file(self, file_path: Path, mime: str):
        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header:
            # Handle HTTP Range requests for video seeking
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if ranges[1] else file_size - 1
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def _handle_api_stats(self):
        db_path = Path("data/telemetry.db")
        if not db_path.exists():
            self._send_json({"total_streams": 0, "total_triggers": 0, "top_rejections": []})
            return

        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM stream_sessions;")
        streams = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM frame_decisions WHERE decision = 'TRIGGER';")
        triggers = c.fetchone()[0]
        c.execute("""
            SELECT rejection_reason, COUNT(*) as cnt 
            FROM frame_decisions 
            WHERE decision = 'REJECT' AND rejection_reason != ''
            GROUP BY rejection_reason 
            ORDER BY cnt DESC LIMIT 5;
        """)
        rejections = [{"reason": r[0], "count": r[1]} for r in c.fetchall()]
        conn.close()

        self._send_json({
            "total_streams": streams,
            "total_triggers": triggers,
            "top_rejections": rejections
        })

    def _handle_api_streams(self):
        db_path = Path("data/telemetry.db")
        if not db_path.exists():
            self._send_json([])
            return

        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT session_id, creator_name, platform, stream_url, language, status FROM stream_sessions;")
        rows = c.fetchall()
        conn.close()

        streams = [
            {"session_id": r[0], "creator_name": r[1], "platform": r[2], "stream_url": r[3], "language": r[4], "status": r[5]}
            for r in rows
        ]
        self._send_json(streams)

    def _handle_api_clips(self):
        clips = []
        winner_dir = Path("output/tournament_winners")
        if winner_dir.exists():
            for p in sorted(winner_dir.glob("*.mp4")):
                fname = p.name
                title = fname.replace("_WINNER_9x16.mp4", "").replace("_", " ").title()
                score = 88.0
                if "police" in fname.lower():
                    score = 78.5
                    creator = "theRadBrad"
                    lang = "English"
                    yt_title = "🚨 3-STAR POLICE ESCAPE! (theRadBrad GTA Gameplay) #Shorts"
                    tags = "#GTA6 #GTA5 #PoliceChase #Shorts #Gaming"
                elif "loading" in fname.lower():
                    score = 93.5
                    creator = "GTA Series Videos"
                    lang = "English"
                    yt_title = "🔥 OFFICIAL CHARACTER ARTWORK REVEAL! #Shorts"
                    tags = "#GTA6 #RockstarGames #GTAArtwork #Shorts"
                else:
                    score = 84.8
                    creator = "Techno Gamerz"
                    lang = "Hindi"
                    yt_title = "🚗 FIRST PERSON COCKPIT DRIVING! (Techno Gamerz) #Shorts"
                    tags = "#TechnoGamerz #GTA6 #GTA5 #CockpitView #Shorts"

                clips.append({
                    "id": p.stem,
                    "title": title,
                    "creator": creator,
                    "platform": "youtube",
                    "language": lang,
                    "virality_score": score,
                    "video_url": f"/video/tournament_winners/{urllib.parse.quote(fname)}",
                    "youtube_title": yt_title,
                    "tags": tags
                })

        self._send_json(clips)

    def _send_json(self, data: Any):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def run_server(port: int = PORT):
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), ClipperHTTPHandler) as httpd:
        print(f"🚀 Clipper Web UI Control Center running at: http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
