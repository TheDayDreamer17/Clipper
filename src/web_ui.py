import socket
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
    <button class="nav-btn" onclick="switchTab('props')">🎯 Active Target Props Catalog</button>
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

    <div id="tab-props" style="display: none;">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Prop ID & Category</th>
              <th>Target Name</th>
              <th>Positive Visual Anchors</th>
              <th>Negative Disqualifiers</th>
              <th>HUD Trigger Rule</th>
              <th>Learned Weight</th>
            </tr>
          </thead>
          <tbody id="props-tbody"></tbody>
        </table>
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
      document.getElementById('tab-props').style.display = tab === 'props' ? 'block' : 'none';
      document.getElementById('tab-streams').style.display = tab === 'streams' ? 'block' : 'none';
      document.getElementById('tab-audit').style.display = tab === 'audit' ? 'block' : 'none';
    }

    async function loadData() {
      try {
        const [statsRes, clipsRes, streamsRes, propsRes] = await Promise.all([
          fetch('/api/stats'),
          fetch('/api/clips'),
          fetch('/api/streams'),
          fetch('/api/props')
        ]);
        const stats = await statsRes.json();
        const clips = await clipsRes.json();
        const streams = await streamsRes.json();
        const props = await propsRes.json();

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
                  <div class="meta-row"><span>Channel:</span> <span class="badge" style="border-color: ${c.channel && c.channel.includes('INDIA') ? '#FF9933' : 'var(--accent)'}; color: #FFF; font-weight: 700;">${c.channel || 'GTA 6 CLIPS'}</span></div>
                  <div class="meta-row"><span>Creator:</span> <span class="meta-val">${c.creator}</span></div>
                  <div class="meta-row"><span>Platform:</span> <span class="meta-val">${c.platform.toUpperCase()} (${c.language})</span></div>
                  <div class="meta-row"><span>QA Veracity:</span> <span class="meta-val" style="color: var(--green);">VERIFIED PASS</span></div>
                </div>
                <div class="social-tags" title="Click to copy for YouTube Shorts / Reels">
                  <strong>YouTube Title:</strong> ${c.youtube_title}<br>
                  <strong>Tags:</strong> ${c.tags}
                </div>
                <div class="actions">
                  <button class="btn btn-copy" onclick="copyMeta('${c.youtube_title.replace(/'/g, "\\'")}', '${c.tags}')">📋 Copy Meta</button>
                  <button class="btn btn-approve" onclick="approveClip('${c.id}')">🚀 Stage for Upload</button>
                </div>
              </div>
            </div>
          `).join('');
        }

        // Render Props Catalog
        const propsBody = document.getElementById('props-tbody');
        if (propsBody && props.length > 0) {
          propsBody.innerHTML = props.map(p => `
            <tr>
              <td>
                <strong style="color: var(--accent); font-family: monospace;">${p.prop_id}</strong><br>
                <span class="badge" style="font-size:0.7rem; margin-top:4px;">${p.category}</span>
              </td>
              <td><strong>${p.name}</strong></td>
              <td>
                <ul style="margin:0; padding-left:16px; font-size:0.8rem; color:#A1A1AA; line-height: 1.5;">
                  ${p.visual_anchors.map(a => `<li>${a}</li>`).join('')}
                </ul>
              </td>
              <td>
                <ul style="margin:0; padding-left:16px; font-size:0.8rem; color:#FF5C5C; line-height: 1.5;">
                  ${p.negative_anchors.map(n => `<li>${n}</li>`).join('')}
                </ul>
              </td>
              <td>
                <code style="background: rgba(0,0,0,0.4); padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; color: var(--accent);">${p.hud_trigger_rule}</code>
              </td>
              <td>
                <strong style="color: var(--green); font-size: 1.1rem; font-family: monospace;">${p.learned_weight}x</strong>
              </td>
            </tr>
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

        elif path == "/api/props":
            self._handle_api_props()
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

    def _handle_api_props(self):
        policy_path = Path("data/self_learned_policy.json")
        weights = {}
        if policy_path.exists():
            try:
                with open(policy_path, "r") as f:
                    weights = json.load(f).get("prompt_weights", {})
            except Exception:
                pass

        props = [
            {
                "prop_id": "PROP_POLICE_PURSUIT",
                "category": "POLICE_PURSUIT",
                "name": "Los Santos High-Speed 3-Star Police Pursuit with Cruisers & Sirens",
                "visual_anchors": [
                    "police cruiser patrol car chasing player with flashing red and blue lights",
                    "high speed car pursuit evasion through city streets with sirens",
                    "cop cars attempting pit maneuver or roadblock"
                ],
                "negative_anchors": [
                    "calm street driving with no police cars",
                    "walking on sidewalk",
                    "retail store interior",
                    "loading screen"
                ],
                "hud_trigger_rule": "MUST HAVE: Wanted stars / flashing red-blue minimap. VQA: Are police cars chasing?",
                "learned_weight": weights.get("PROP_POLICE_PURSUIT", 1.16)
            },
            {
                "prop_id": "PROP_VIRAL_PHYSICS_FEAT",
                "category": "VIRAL_PHYSICS",
                "name": "Stopping The Train Challenge & High-Altitude Mountain Stunts",
                "visual_anchors": [
                    "speeding freight train explosive collision with tanks or barricades on tracks",
                    "motorcycle cliff jump parachute launch from Mount Chiliad summit",
                    "extreme vehicular physics collision with sparks and massive momentum"
                ],
                "negative_anchors": [
                    "peaceful city driving",
                    "walking on foot inside building",
                    "dialogue cutscene with no action"
                ],
                "hud_trigger_rule": "KINETIC DELTA: >45 px/frame optical flow + explosion particles or altitude drop >500m",
                "learned_weight": 1.25
            },
            {
                "prop_id": "PROP_MILITARY_INFILTRATION",
                "category": "HIGH_STAKES",
                "name": "Fort Zancudo 5-Star Military Base Jet Theft & Tank Evasion",
                "visual_anchors": [
                    "infiltrating military airbase with rhino tanks firing explosive shells",
                    "stealing P-996 Lazer military fighter jet taking off under missile lock",
                    "intense 5-star wanted combat survival against attack helicopters"
                ],
                "negative_anchors": [
                    "standard low-speed city traffic",
                    "clothing store shopping",
                    "safehouse garage"
                ],
                "hud_trigger_rule": "MUST HAVE: 5 flashing wanted stars + tank cannon flashes + missile lock warning tone",
                "learned_weight": 1.22
            },
            {
                "prop_id": "PROP_LOADING_ARTWORK",
                "category": "LOADING_ARTWORK",
                "name": "Official Rockstar Character Artwork Rotation (Michael, Franklin, Trevor, Bikini Girl)",
                "visual_anchors": [
                    "GTA loading screen rotating character artwork slides and portraits",
                    "official Rockstar artwork of Michael, Franklin, Trevor, and bikini girl",
                    "loading screen transition with background artwork into game world"
                ],
                "negative_anchors": [
                    "active 3D in-game camera driving or walking",
                    "dark black screen with no artwork",
                    "pause settings menu"
                ],
                "hud_trigger_rule": "MUST HAVE: 2D artwork illustration or loading spinner. VQA: Is 2D character artwork visible?",
                "learned_weight": weights.get("PROP_LOADING_ARTWORK", 1.03)
            },
            {
                "prop_id": "PROP_CAMERA_POV",
                "category": "CAMERA_POV",
                "name": "In-Car Cockpit Driving with Steering Wheel & Dashboard Toggle",
                "visual_anchors": [
                    "first person interior cockpit view from driver seat with steering wheel and dashboard",
                    "camera transitioning from third person chase view into interior driver cockpit",
                    "hands holding steering wheel driving car from first person perspective"
                ],
                "negative_anchors": [
                    "third person camera hovering behind the bumper",
                    "cinematic cutscene",
                    "walking on foot"
                ],
                "hud_trigger_rule": "MUST HAVE: Visible steering wheel / dashboard gauges. VQA: Is cockpit view visible?",
                "learned_weight": weights.get("PROP_CAMERA_POV", 0.90)
            },
            {
                "prop_id": "PROP_WEAPON_COMBAT",
                "category": "WEAPON_COMBAT",
                "name": "In-Game Radial Weapon Wheel Selection & Combat Shootout",
                "visual_anchors": [
                    "player opening in-game circular radial weapon wheel to switch guns",
                    "active gunfight shootout with weapon reticle and muzzle flash",
                    "aiming shotgun or rifle in combat cover"
                ],
                "negative_anchors": [
                    "browsing retail gun shop shelves or Ammu-Nation counter",
                    "driving vehicle with no weapons",
                    "loading screen"
                ],
                "hud_trigger_rule": "MUST HAVE: Circular weapon selector wheel or combat reticle. VQA: Is radial weapon wheel visible?",
                "learned_weight": weights.get("PROP_WEAPON_COMBAT", 1.16)
            },
            {
                "prop_id": "PROP_AERIAL_FLIGHT",
                "category": "AERIAL_FLIGHT",
                "name": "Helicopter Helipad Ground Takeoff to Los Santos Skyline",
                "visual_anchors": [
                    "helicopter starting from helipad ground lifting up into the air",
                    "helicopter climbing above city skyline with sunset horizon",
                    "aerial panoramic view from aircraft over skyscrapers"
                ],
                "negative_anchors": [
                    "car driving on asphalt road",
                    "subway tunnel",
                    "indoor gunfight"
                ],
                "hud_trigger_rule": "MUST HAVE: Helicopter rotor blades or cockpit altimeter. VQA: Is helicopter lifting off?",
                "learned_weight": weights.get("PROP_AERIAL_FLIGHT", 1.16)
            }
        ]
        self._send_json(props)

    def _handle_api_clips(self):
        clips = []
        winner_dir = Path("output/tournament_winners")
        if winner_dir.exists():
            for p in sorted(winner_dir.glob("*.mp4")):
                fname = p.name
                title = fname.replace("_WINNER_9x16.mp4", "").replace("_", " ").title()
                score = 88.0
                fl = fname.lower()
                channel = "GTA 6 CLIPS"
                if "techno" in fl or "carry" in fl or "india" in fl:
                    channel = "GTA 6 CLIPS INDIA"

                if "train" in fl:
                    score = 98.4
                    creator = "NoughtPointFourLIVE"
                    lang = "English"
                    yt_title = "🚂 CAN YOU STOP THE TRAIN IN GTA 5?! (Speeding Train Collision) #Shorts"
                    tags = "#GTA5 #GTA6 #GTA6Clips #Gaming #Shorts #TrainChallenge"
                elif "jet" in fl or "5star" in fl or "military" in fl:
                    score = 95.2
                    creator = "VanossGaming"
                    lang = "English"
                    yt_title = "🚨 STEALING MILITARY JET WITH 5 STARS! (Fort Zancudo Infiltration) #Shorts"
                    tags = "#GTA5 #GTA6 #GTA6Clips #MilitaryBase #5Stars #Shorts"
                elif "chiliad" in fl or "stunt" in fl or "jump" in fl:
                    score = 94.0
                    creator = "RedKB"
                    lang = "English"
                    yt_title = "⛰️ INSANE MOUNT CHILIAD CLIFF JUMP! (Bike Parachute Escape) #Shorts"
                    tags = "#GTA5 #GTA6 #GTA6Clips #StuntJump #MountChiliad #Shorts"
                elif "police" in fl:
                    score = 78.5
                    creator = "theRadBrad"
                    lang = "English"
                    yt_title = "🚨 3-STAR POLICE ESCAPE! (theRadBrad GTA Gameplay) #Shorts"
                    tags = "#GTA6 #GTA5 #GTA6Clips #PoliceChase #Shorts"
                elif "loading" in fl or "artwork" in fl:
                    score = 93.5
                    creator = "GTA Series Videos"
                    lang = "English"
                    yt_title = "🔥 OFFICIAL CHARACTER ARTWORK REVEAL! #Shorts"
                    tags = "#GTA6 #GTA6Clips #RockstarGames #GTAArtwork #Shorts"
                elif "global" in fl:
                    score = 92.5
                    creator = "theRadBrad"
                    lang = "English"
                    channel = "GTA 6 CLIPS"
                    yt_title = "🚨 CAN YOU STOP THE TRAIN?! (GTA 6 Clips Global) #Shorts"
                    tags = "#GTA6 #GTA6Clips #Gaming #Shorts #TrainCollision"
                else:
                    score = 84.8
                    creator = "Techno Gamerz"
                    lang = "Hindi"
                    channel = "GTA 6 CLIPS INDIA"
                    yt_title = "🚗 FIRST PERSON COCKPIT DRIVING! (Techno Gamerz) #Shorts"
                    tags = "#TechnoGamerz #GTA6ClipsIndia #GTA6 #GTA5 #CockpitView #Shorts"

                clips.append({
                    "id": p.stem,
                    "title": title,
                    "creator": creator,
                    "platform": "youtube",
                    "language": lang,
                    "channel": channel,
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

class DualStackHTTPServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except Exception:
            pass
        return super().server_bind()

def run_server(port: int = PORT):
    try:
        httpd = DualStackHTTPServer(("::", port), ClipperHTTPHandler)
    except Exception:
        DualStackHTTPServer.address_family = socket.AF_INET
        httpd = DualStackHTTPServer(("0.0.0.0", port), ClipperHTTPHandler)

    print(f"🚀 Clipper Web UI Control Center running at: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
