import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import socket
import http.server
import socketserver
import json
import urllib.parse
import mimetypes
import sqlite3
import time
import subprocess
from typing import Dict, List, Any

from src.agent_swarm import AgentSwarmCoordinator
from src.self_learner import SelfLearningEngine
from src.slicer import VideoSlicer
from src.twitch_clips import TwitchClipEngine
from src.fetcher import StreamFetcher
from src.ingest import StreamIngester
from src.seo_engine import ViralSEOEngine
from src.publisher import VideoPublisher
from src.transcribe import Transcriber
from src.scorer import ViralityScorer
from src.semantic_gatekeeper import SemanticGatekeeper
from src.portal_ui import RAVI_PORTAL_HTML, get_ravi_candidate_clips, submit_ravi_feedback, search_stream_journals, get_stream_registry, rescan_stream, snip_moment

import os
PORT = int(os.environ.get("CLIPPER_PORT", 3000))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Outlaw Clips Executive Hub</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #09080E;
      --card: #121019;
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(255, 255, 255, 0.12);
      --coral: #FF2A6D;
      --cyan: #00F0FF;
      --gold: #FFB800;
      --green: #00E676;
      --text: #F1F0F5;
      --text-muted: #8E8A9F;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* TOP APP HEADER */
    header {
      background: rgba(14, 11, 22, 0.9);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--card-border);
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-logo {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--coral), #9B55C6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 16px;
      box-shadow: 0 0 16px rgba(255, 42, 109, 0.4);
    }
    .brand-title {
      font-size: 17px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    .brand-badge {
      font-size: 10px;
      background: rgba(0, 240, 255, 0.12);
      color: var(--cyan);
      border: 1px solid rgba(0, 240, 255, 0.3);
      padding: 2px 8px;
      border-radius: 20px;
      font-weight: 700;
      letter-spacing: 0.05em;
    }

    .top-stats {
      display: flex;
      align-items: center;
      gap: 20px;
    }
    .stat-chip {
      background: var(--card);
      border: 1px solid var(--card-border);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .stat-val {
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }
    .btn-ingest {
      background: linear-gradient(135deg, var(--coral), #9B55C6);
      color: #fff;
      border: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 0 16px rgba(255, 42, 109, 0.35);
      transition: all 0.2s;
    }
    .btn-ingest:hover {
      transform: translateY(-1px);
      box-shadow: 0 0 22px rgba(255, 42, 109, 0.55);
    }

    /* MAIN EXECUTIVE LAYOUT: 70% / 30% SPLIT RAIL */
    main {
      display: grid;
      grid-template-columns: 1fr 360px;
      gap: 24px;
      padding: 24px 28px;
      flex: 1;
      max-width: 1720px;
      margin: 0 auto;
      width: 100%;
    }

    /* LEFT ZONE: CLIPS & REVIEW HUB */
    .left-zone {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .filter-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 14px;
    }
    .filter-group {
      display: flex;
      gap: 8px;
    }
    .tab-btn {
      background: var(--card);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .tab-btn:hover {
      border-color: var(--card-hover);
      color: var(--text);
    }
    .tab-btn.active {
      background: var(--coral);
      border-color: var(--coral);
      color: #fff;
      box-shadow: 0 0 12px rgba(255, 42, 109, 0.35);
    }
    .badge-count {
      background: rgba(0, 0, 0, 0.25);
      padding: 1px 6px;
      border-radius: 12px;
      font-size: 11px;
    }

    /* CLIPS GRID */
    .clips-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }
    .clip-card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: all 0.2s;
      position: relative;
    }
    .clip-card:hover {
      border-color: var(--card-hover);
      transform: translateY(-2px);
    }
    .clip-card.highlight {
      border: 1px solid rgba(0, 240, 255, 0.4);
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.12);
    }
    .video-wrap {
      position: relative;
      width: 100%;
      aspect-ratio: 9/16;
      max-height: 380px;
      background: #000;
    }
    .video-wrap video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .score-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(12, 10, 18, 0.88);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 3px 8px;
      border-radius: 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .score-badge.high { color: var(--green); border-color: rgba(0, 230, 118, 0.4); }
    .score-badge.med { color: var(--gold); border-color: rgba(255, 184, 0, 0.4); }
    .score-badge.low { color: var(--coral); border-color: rgba(255, 42, 109, 0.4); }

    .nsfw-badge {
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(255, 42, 109, 0.9);
      color: #fff;
      font-size: 10px;
      font-weight: 800;
      padding: 3px 7px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }
    .safe-badge {
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(0, 230, 118, 0.9);
      color: #000;
      font-size: 10px;
      font-weight: 800;
      padding: 3px 7px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }

    .clip-info {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
    }
    .clip-title {
      font-size: 13px;
      font-weight: 700;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .clip-meta-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-muted);
    }
    .creator-pill {
      color: var(--cyan);
      font-weight: 600;
    }
    .btn-review-ok {
      margin-top: auto;
      background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(255, 42, 109, 0.15));
      border: 1px solid var(--card-border);
      color: var(--text);
      font-weight: 700;
      font-size: 12px;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn-review-ok:hover {
      background: linear-gradient(135deg, var(--coral), #9B55C6);
      border-color: transparent;
      color: #fff;
    }

    /* RIGHT ZONE: LIVE INTELLIGENCE RAIL */
    .right-zone {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .intel-card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .intel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--card-border);
    }
    .intel-title {
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .live-dot {
      width: 7px;
      height: 7px;
      background: var(--coral);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--coral);
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

    /* STREAM LIST */
    .stream-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .stream-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 6px;
      font-size: 12px;
    }
    .stream-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .stream-name { font-weight: 600; }
    .stream-plat { font-size: 10px; color: var(--text-muted); }

    /* TRENDS LIST */
    .trend-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .trend-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      padding: 6px 8px;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 4px;
    }
    .trend-query { font-weight: 600; color: var(--text); }
    .trend-vel { color: var(--coral); font-family: 'JetBrains Mono', monospace; font-size: 10px; }

    /* PROPS LIST */
    .prop-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .prop-item {
      padding: 8px;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 6px;
      border-left: 2px solid var(--cyan);
      font-size: 11px;
    }
    .prop-title { font-weight: 700; color: #fff; margin-bottom: 2px; }
    .prop-desc { color: var(--text-muted); font-size: 10px; }

    /* MODAL: REVIEW & SOCIAL DISPATCH */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(5, 4, 8, 0.85);
      backdrop-filter: blur(12px);
      z-index: 100;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-card {
      background: #110F18;
      border: 1px solid var(--card-border);
      border-radius: 16px;
      width: 100%;
      max-width: 900px;
      max-height: 90vh;
      display: grid;
      grid-template-columns: 340px 1fr;
      overflow: hidden;
      box-shadow: 0 0 40px rgba(0, 0, 0, 0.8);
    }
    .modal-video-pane {
      background: #000;
      display: flex;
      align-items: center;
      justify-content: center;
      border-right: 1px solid var(--card-border);
      position: relative;
    }
    .modal-video-pane video {
      width: 100%;
      height: 100%;
      max-height: 80vh;
      object-fit: contain;
    }
    .modal-meta-pane {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow-y: auto;
    }
    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--card-border);
    }
    .modal-title { font-size: 16px; font-weight: 800; }
    .btn-close {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }
    .meta-block {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .meta-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--cyan);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .meta-content {
      font-size: 12px;
      color: var(--text);
      line-height: 1.4;
      white-space: pre-wrap;
      max-height: 120px;
      overflow-y: auto;
      font-family: 'JetBrains Mono', monospace;
    }
    .copy-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 10px;
      cursor: pointer;
    }
    .copy-btn:hover { background: rgba(255, 255, 255, 0.12); }
    .modal-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: auto;
      padding-top: 12px;
      border-top: 1px solid var(--card-border);
    }
    .btn-confirm-publish {
      flex: 1;
      background: linear-gradient(135deg, var(--coral), #9B55C6);
      color: #fff;
      border: none;
      padding: 10px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      box-shadow: 0 0 16px rgba(255, 42, 109, 0.3);
    }

    /* SOCIAL CHANNELS REAL-TIME METRICS BAR */
    .social-channels-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      padding: 16px 28px 0 28px;
    }
    .social-card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all 0.2s ease;
    }
    .social-card:hover {
      border-color: var(--card-hover);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .sc-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .sc-title {
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .sc-pill {
      font-size: 9px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }
    .sc-pill.live {
      background: rgba(0, 230, 118, 0.15);
      color: var(--green);
      border: 1px solid rgba(0, 230, 118, 0.3);
    }
    .sc-pill.shielded {
      background: rgba(0, 240, 255, 0.15);
      color: var(--cyan);
      border: 1px solid rgba(0, 240, 255, 0.3);
    }
    .sc-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.04);
      border-radius: 8px;
      padding: 8px 10px;
    }
    .sc-stat {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .sc-label {
      font-size: 9px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .sc-val {
      font-size: 15px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      color: #fff;
    }
    .sc-recent {
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .sc-recent a {
      color: var(--cyan);
      text-decoration: none;
      font-weight: 600;
      max-width: 220px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .sc-recent a:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>

  <!-- TOP HEADER -->
  <header>
    <div class="brand">
      <div class="brand-logo">OC</div>
      <div>
        <div class="brand-title">Outlaw Clips Command Hub</div>
        <div class="brand-badge">Autonomous Clipper 2.0</div>
      </div>
    </div>

    <div class="top-stats">
      <div class="stat-chip">
        <span>🎬 Total Clips:</span>
        <span class="stat-val" id="stat-total">0</span>
      </div>
      <div class="stat-chip">
        <span style="color:var(--green)">⭐ In Review:</span>
        <span class="stat-val" style="color:var(--green)" id="stat-review">0</span>
      </div>
      <div class="stat-chip">
        <span style="color:var(--cyan)">📥 Queued:</span>
        <span class="stat-val" style="color:var(--cyan)" id="stat-queued">0</span>
      </div>
      <div class="stat-chip">
        <span style="color:var(--coral)">⚠️ Failed:</span>
        <span class="stat-val" style="color:var(--coral)" id="stat-failed">0</span>
      </div>
      <div class="stat-chip">
        <span style="color:var(--coral)">🔞 NSFW:</span>
        <span class="stat-val" style="color:var(--coral)" id="stat-nsfw">0</span>
      </div>
      <div class="stat-chip" style="border-color:rgba(0, 240, 255, 0.3); background:rgba(0, 240, 255, 0.08);">
        <span style="color:var(--cyan)">⏰ Auto-Pilot:</span>
        <span class="stat-val" style="color:var(--cyan); font-size:11px;">Active 🚀</span>
      </div>
      <button class="btn-ingest" onclick="ingestFreshLiveClip()">
        <span>🔴 Ingest Live Clip</span>
      </button>
      <button class="btn-reset" style="background: rgba(255, 42, 109, 0.15); border: 1px solid rgba(255, 42, 109, 0.4); color: var(--coral); padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer;" onclick="resetCacheAndDB()">
        <span>🧹 Wipe Cache &amp; Reset</span>
      </button>
    </div>
  </header>

  <!-- SOCIAL CHANNELS REAL-TIME METRICS BAR -->
  <div class="social-channels-bar">
    <!-- Card 1: YouTube US Global -->
    <div class="social-card">
      <div class="sc-header">
        <span class="sc-title">🇺🇸 <a href="https://www.youtube.com/@outlawclipsglobal" target="_blank" style="color:#fff; text-decoration:none;">YouTube Global (@OutlawClipsGlobal)</a></span>
        <span class="sc-pill live" id="pill-yt-us">API LIVE 🟢</span>
      </div>
      <div class="sc-stats">
        <div class="sc-stat"><span class="sc-label">Subscribers</span><span class="sc-val" id="sc-us-subs">-</span></div>
        <div class="sc-stat"><span class="sc-label">Lifetime Views</span><span class="sc-val" id="sc-us-views">-</span></div>
        <div class="sc-stat"><span class="sc-label">Shorts Live</span><span class="sc-val" id="sc-us-vids">-</span></div>
      </div>
      <div class="sc-recent">
        <span>Latest:</span>
        <span id="sc-us-recent" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Loading...</span>
      </div>
    </div>

    <!-- Card 2: YouTube India -->
    <div class="social-card">
      <div class="sc-header">
        <span class="sc-title">🇮🇳 <a href="https://www.youtube.com/@outlawclipshq" target="_blank" style="color:#fff; text-decoration:none;">YouTube India (@OutlawClipsHindi)</a></span>
        <span class="sc-pill live" id="pill-yt-in">API LIVE 🟢</span>
      </div>
      <div class="sc-stats">
        <div class="sc-stat"><span class="sc-label">Subscribers</span><span class="sc-val" id="sc-in-subs">-</span></div>
        <div class="sc-stat"><span class="sc-label">Lifetime Views</span><span class="sc-val" id="sc-in-views">-</span></div>
        <div class="sc-stat"><span class="sc-label">Shorts Live</span><span class="sc-val" id="sc-in-vids">-</span></div>
      </div>
      <div class="sc-recent">
        <span>Latest:</span>
        <span id="sc-in-recent" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Loading...</span>
      </div>
    </div>

    <!-- Card 3: Instagram -->
    <div class="social-card">
      <div class="sc-header">
        <span class="sc-title">📸 <a href="https://www.instagram.com/outlawclipshq/" target="_blank" style="color:#fff; text-decoration:none;">Instagram (@outlawclipshq)</a></span>
        <span class="sc-pill shielded">GUARDRAIL ACTIVE 🛡️</span>
      </div>
      <div class="sc-stats">
        <div class="sc-stat"><span class="sc-label">Followers</span><span class="sc-val" id="sc-ig-followers">1</span></div>
        <div class="sc-stat"><span class="sc-label">Live Reels</span><span class="sc-val" id="sc-ig-reels">20</span></div>
        <div class="sc-stat"><span class="sc-label">Clipper Total</span><span class="sc-val" id="sc-ig-clipper">25</span></div>
      </div>
      <div class="sc-recent">
        <span style="color:var(--text-muted)">Safety Pacing:</span>
        <span style="color:var(--cyan); font-weight:600;">2.5h Anti-Spam Cooldown</span>
      </div>
    </div>
  </div>

  <!-- MAIN EXEC LAYOUT -->
  <main>
    <!-- LEFT ZONE: CLIPS & REVIEW HUB -->
    <div class="left-zone">
      <div class="filter-bar">
        <div class="filter-group">
          <button class="tab-btn active" onclick="setFilter('review')">
            <span>⭐ Review Queue</span>
            <span class="badge-count" id="count-review">0</span>
          </button>
          <button class="tab-btn" onclick="setFilter('queued')">
            <span>📥 Queued for Dispatch</span>
            <span class="badge-count" id="count-queued">0</span>
          </button>
          <button class="tab-btn" onclick="setFilter('failed')">
            <span>⚠️ Failed Dispatches</span>
            <span class="badge-count" id="count-failed" style="background:#FF2A6D; color:#fff;">0</span>
          </button>
          <button class="tab-btn" onclick="setFilter('published')">
            <span>🚀 Published</span>
            <span class="badge-count" id="count-published">0</span>
          </button>
          <button class="tab-btn" onclick="setFilter('safe')">
            <span>✅ Safe Gameplay</span>
            <span class="badge-count" id="count-safe">0</span>
          </button>
          <button class="tab-btn" onclick="setFilter('all')">
            <span>🎬 All Clips</span>
            <span class="badge-count" id="count-all">0</span>
          </button>
          <button class="tab-btn" onclick="setFilter('nsfw')">
            <span>🔞 NSFW Censored</span>
            <span class="badge-count" id="count-nsfw">0</span>
          </button>
        </div>
      </div>

      <!-- CLIPS GRID -->
      <div class="clips-grid" id="clips-grid">
        <!-- Rendered dynamically via JS -->
      </div>
    </div>

    <!-- RIGHT ZONE: LIVE INTELLIGENCE RAIL -->
    <div class="right-zone">
      <!-- 1. STREAMS WE ARE FOLLOWING -->
      <div class="intel-card">
        <div class="intel-header">
          <div class="intel-title">
            <span class="live-dot"></span>
            <span>Streams Following</span>
          </div>
          <span style="font-size:10px; color:var(--text-muted);">Real-Time</span>
        </div>
        <div class="stream-list" id="stream-list">
          <div style="font-size:11px; color:var(--text-muted);">Loading live streams...</div>
        </div>
      </div>

      <!-- 2. REAL-TIME TRENDS MINED -->
      <div class="intel-card">
        <div class="intel-header">
          <div class="intel-title">
            <span>🔥 15-Min Live Trends</span>
          </div>
          <span style="font-size:10px; color:var(--cyan);">Top Searches</span>
        </div>
        <div class="trend-list" id="trend-list">
          <div style="font-size:11px; color:var(--text-muted);">Mined from YouTube autocomplete...</div>
        </div>
      </div>

      <!-- 3. TARGET PROPS CATALOG -->
      <div class="intel-card">
        <div class="intel-header">
          <div class="intel-title">
            <span>🎯 Active Target Props</span>
          </div>
          <span style="font-size:10px; color:var(--gold);">Bounties</span>
        </div>
        <div class="prop-list" id="prop-list">
          <div style="font-size:11px; color:var(--text-muted);">Loading active props...</div>
        </div>
      </div>
    </div>
  </main>

  <!-- MODAL: REVIEW & SOCIAL DISPATCH -->
  <div class="modal-overlay" id="review-modal">
    <div class="modal-card">
      <div class="modal-video-pane">
        <video id="modal-video" controls autoplay loop playsinline></video>
      </div>
      <div class="modal-meta-pane">
        <div class="modal-header">
          <div>
            <div class="modal-title" id="modal-headline">Ready for Social Dispatch</div>
            <div style="font-size:11px; color:var(--cyan);" id="modal-creator-tag">@Creator</div>
          </div>
          <button class="btn-close" onclick="closeReviewModal()">&times;</button>
        </div>

        <!-- NSFW / CENSOR OVERRIDE TOOLBAR -->
        <div id="modal-nsfw-bar" style="display:none; background:#221018; border:1px solid rgba(255,42,109,0.5); padding:10px 14px; border-radius:8px; margin-bottom:12px; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
          <span style="font-size:12px; font-weight:700; color:#FF2A6D;">🔞 Mature Scene Guardrail</span>
          <div style="display:flex; gap:8px;">
            <button style="background:#0F291E; border:1px solid #00FFA3; color:#00FFA3; font-weight:700; padding:6px 12px; border-radius:6px; font-size:11px; cursor:pointer;" onclick="unblurActiveModalClip()">
              🔓 Mark Safe &amp; Remove Blur
            </button>
            <button style="background:#1F1128; border:1px solid #00F0FF; color:#00F0FF; font-weight:700; padding:6px 12px; border-radius:6px; font-size:11px; cursor:pointer;" onclick="recensorActiveModalClip()">
              🛡️ Recensor with Circular Logo
            </button>
          </div>
        </div>

        <!-- QUICK CLIP TRIMMER TOOLBAR -->
        <div style="background:#13111E; border:1px solid rgba(0,240,255,0.25); padding:10px 14px; border-radius:8px; margin-bottom:12px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-size:12px; font-weight:700; color:#00F0FF;">✂️ Clip Trimmer</span>
            <span id="modal-trim-current-dur" style="font-size:11px; color:var(--text-muted); font-family:monospace;"></span>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <button id="btn-trim-3s" style="background:#1C162E; border:1px solid #7928CA; color:#E087FF; font-weight:700; padding:6px 12px; border-radius:6px; font-size:11px; cursor:pointer; transition:0.15s;" onclick="trimActiveModalClip(3.0)">
              ✂️ Cut Last 3s
            </button>
            <button id="btn-trim-5s" style="background:#1C162E; border:1px solid #7928CA; color:#E087FF; font-weight:700; padding:6px 12px; border-radius:6px; font-size:11px; cursor:pointer; transition:0.15s;" onclick="trimActiveModalClip(5.0)">
              ✂️ Cut Last 5s
            </button>
            <button id="btn-trim-custom" style="background:#181A26; border:1px solid rgba(255,255,255,0.2); color:#fff; font-weight:600; padding:6px 10px; border-radius:6px; font-size:11px; cursor:pointer;" onclick="trimActiveModalClipCustom()">
              ✂️ Custom Cut...
            </button>
          </div>
        </div>

        <!-- DISPATCH FAILURE BANNER -->
        <div id="modal-failed-bar" style="display:none; background:#2A141D; border:1px solid #FF2A6D; padding:10px 14px; border-radius:8px; margin-bottom:12px; color:#FF809B; font-size:12px;">
          <div style="font-weight:700; color:#FF2A6D; margin-bottom:4px;">⚠️ Previous Dispatch Failed:</div>
          <div id="modal-failed-msg" style="word-break:break-word; font-family:monospace; font-size:11px; color:#fff;"></div>
        </div>

        <!-- YOUTUBE SHORTS PACKAGE -->
        <div class="meta-block">
          <div class="meta-label">
            <span>📺 YouTube Shorts Metadata</span>
            <button class="copy-btn" onclick="copyText('modal-yt-title')">Copy Title</button>
          </div>
          <div style="font-size:11px; font-weight:700; color:#fff;" id="modal-yt-title">Title loading...</div>
          <div class="meta-content" id="modal-yt-desc">Description loading...</div>
          <div style="font-size:10px; color:var(--text-muted); margin-top:4px;" id="modal-yt-tags">Tags loading...</div>
        </div>

        <!-- INSTAGRAM REELS PACKAGE -->
        <div class="meta-block">
          <div class="meta-label">
            <span>📸 Instagram Reels Caption &amp; Hashtags</span>
            <button class="copy-btn" onclick="copyText('modal-ig-caption')">Copy Caption</button>
          </div>
          <div class="meta-content" id="modal-ig-caption">Caption loading...</div>
        </div>

        <!-- PINNED MONETIZATION COMMENT -->
        <div class="meta-block">
          <div class="meta-label">
            <span>🛒 Pinned Monetization Comment</span>
            <button class="copy-btn" onclick="copyText('modal-pinned-comment')">Copy Pinned</button>
          </div>
          <div class="meta-content" id="modal-pinned-comment">Pinned comment loading...</div>
        </div>

        <div class="modal-actions" style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
          <button id="modal-btn-queue" class="btn-confirm-publish" style="background:linear-gradient(135deg, #00F0FF, #0072FF); padding:12px 20px; border-radius:8px; border:none; color:white; font-weight:700; cursor:pointer;" onclick="queueActiveModalClip()">
            📥 Add to Dispatch Queue
          </button>
          <button class="btn-confirm-publish" style="background:linear-gradient(135deg, #FF0055, #9B55C6); padding:12px 20px; border-radius:8px; border:none; color:white; font-weight:700; cursor:pointer;" onclick="dispatchPublish('both')">
            🚀 1-Click Publish Now
          </button>
          <button class="btn-confirm-publish" style="background:#1B1724; border:1px solid rgba(255,255,255,0.15); padding:12px 16px; border-radius:8px; color:white; font-weight:600; cursor:pointer;" onclick="dispatchPublish('youtube')">
            ▶️ YouTube Shorts
          </button>
          <button class="btn-confirm-publish" style="background:#1B1724; border:1px solid rgba(255,255,255,0.15); padding:12px 16px; border-radius:8px; color:white; font-weight:600; cursor:pointer;" onclick="dispatchPublish('instagram')">
            📸 Instagram Reels
          </button>
          <button style="background:#2A141D; border:1px solid rgba(255,42,109,0.5); padding:12px 16px; border-radius:8px; color:#FF2A6D; font-weight:600; cursor:pointer; margin-left:auto;" onclick="deleteClipFromModal()">
            🗑️ Delete Clip
          </button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let allClips = [];
    let currentFilter = 'review';
    let activeModalClip = null;

    async function loadData() {
      // 1. Fetch training clips with top priority and render immediately
      try {
        const res = await fetch('/api/training_clips?t=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        allClips = await res.json();
        renderClips();
        updateCounts();
      } catch (err) {
        console.error("Clips load failed:", err);
        const grid = document.getElementById('clips-grid');
        if (grid) {
          grid.innerHTML = `<div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--coral);">
            ⚠️ Data load issue on cellular network: ${err.message}<br>
            <button onclick="loadData()" style="margin-top:12px; padding:8px 20px; border-radius:6px; background:#FF2A6D; color:#fff; border:none; cursor:pointer; font-weight:700;">🔄 Tap to Reload Clips</button>
          </div>`;
        }
      }

      // 2. Fetch auxiliary telemetry in parallel without blocking clip cards
      fetch('/api/streams?t=' + Date.now(), { cache: 'no-store' })
        .then(r => r.json())
        .then(renderStreams)
        .catch(e => console.warn("Streams warn:", e));

      fetch('/api/trends?t=' + Date.now(), { cache: 'no-store' })
        .then(r => r.json())
        .then(renderTrends)
        .catch(e => console.warn("Trends warn:", e));

      fetch('/api/props?t=' + Date.now(), { cache: 'no-store' })
        .then(r => r.json())
        .then(renderProps)
        .catch(e => console.warn("Props warn:", e));

      fetch('/api/analytics?t=' + Date.now(), { cache: 'no-store' })
        .then(r => r.json())
        .then(renderAnalytics)
        .catch(e => console.warn("Analytics warn:", e));
    }

    function renderAnalytics(data) {
      if (!data) return;
      const us = data.youtube_us;
      if (us && us.status === 'online') {
        const subsEl = document.getElementById('sc-us-subs');
        const viewsEl = document.getElementById('sc-us-views');
        const vidsEl = document.getElementById('sc-us-vids');
        const recentEl = document.getElementById('sc-us-recent');
        if (subsEl) subsEl.innerText = Number(us.subscribers).toLocaleString();
        if (viewsEl) viewsEl.innerText = Number(us.total_views).toLocaleString();
        if (vidsEl) vidsEl.innerText = us.video_count;
        if (recentEl && us.recent_videos && us.recent_videos.length > 0) {
          const top = us.recent_videos[0];
          recentEl.innerHTML = `<a href="${top.url}" target="_blank">▶️ ${top.title.substring(0, 24)}... (${top.views} views)</a>`;
        }
      }

      const ind = data.youtube_india;
      if (ind && ind.status === 'online') {
        const subsEl = document.getElementById('sc-in-subs');
        const viewsEl = document.getElementById('sc-in-views');
        const vidsEl = document.getElementById('sc-in-vids');
        const recentEl = document.getElementById('sc-in-recent');
        if (subsEl) subsEl.innerText = Number(ind.subscribers).toLocaleString();
        if (viewsEl) viewsEl.innerText = Number(ind.total_views).toLocaleString();
        if (vidsEl) vidsEl.innerText = ind.video_count;
        if (recentEl && ind.recent_videos && ind.recent_videos.length > 0) {
          const top = ind.recent_videos[0];
          recentEl.innerHTML = `<a href="${top.url}" target="_blank">▶️ ${top.title.substring(0, 24)}... (${top.views} views)</a>`;
        }
      }

      const ig = data.instagram;
      if (ig) {
        const follEl = document.getElementById('sc-ig-followers');
        const reelsEl = document.getElementById('sc-ig-reels');
        const clipEl = document.getElementById('sc-ig-clipper');
        if (follEl) follEl.innerText = ig.followers;
        if (reelsEl) reelsEl.innerText = ig.posts_count;
        if (clipEl && ig.published_via_clipper) clipEl.innerText = ig.published_via_clipper;
      }
    }

    function updateCounts() {
      const queuedClips = allClips.filter(c => c.human_verdict === 'QUEUED' && c.video_path);
      const failedClips = allClips.filter(c => c.human_verdict === 'FAILED');
      const pendingClips = allClips.filter(c => c.human_verdict !== 'PUBLISHED' && c.human_verdict !== 'FAILED' && c.human_verdict !== 'REJECTED_NSFW_TOMBSTONE' && c.human_verdict !== 'DELETED' && c.video_path);
      const publishedClips = allClips.filter(c => c.human_verdict === 'PUBLISHED');
      const safeCount = pendingClips.filter(c => !c.is_nsfw).length;
      const nsfwCount = allClips.filter(c => c.is_nsfw && c.video_path).length;

      document.getElementById('stat-total').innerText = allClips.filter(c => c.video_path).length;
      document.getElementById('stat-review').innerText = pendingClips.length;
      document.getElementById('stat-queued').innerText = queuedClips.length;
      document.getElementById('stat-failed').innerText = failedClips.length;
      document.getElementById('stat-nsfw').innerText = nsfwCount;

      document.getElementById('count-review').innerText = pendingClips.length;
      document.getElementById('count-queued').innerText = queuedClips.length;
      document.getElementById('count-failed').innerText = failedClips.length;
      const pubEl = document.getElementById('count-published');
      if (pubEl) pubEl.innerText = publishedClips.length;
      document.getElementById('count-safe').innerText = safeCount;
      document.getElementById('count-all').innerText = allClips.filter(c => c.video_path).length;
      document.getElementById('count-nsfw').innerText = nsfwCount;
    }

    function setFilter(filter) {
      currentFilter = filter;
      document.querySelectorAll('.filter-group .tab-btn').forEach(btn => btn.classList.remove('active'));
      const activeBtn = Array.from(document.querySelectorAll('.filter-group .tab-btn')).find(b => b.getAttribute('onclick')?.includes(filter));
      if (activeBtn) activeBtn.classList.add('active');
      renderClips();
    }

    function renderClips() {
      const grid = document.getElementById('clips-grid');
      grid.innerHTML = '';

      let filtered = allClips;
      if (currentFilter === 'review') {
        filtered = allClips.filter(c => c.human_verdict !== 'PUBLISHED' && c.human_verdict !== 'FAILED' && c.human_verdict !== 'REJECTED_NSFW_TOMBSTONE' && c.human_verdict !== 'DELETED' && c.video_path);
      } else if (currentFilter === 'queued') {
        filtered = allClips.filter(c => c.human_verdict === 'QUEUED' && c.video_path);
      } else if (currentFilter === 'failed') {
        filtered = allClips.filter(c => c.human_verdict === 'FAILED');
      } else if (currentFilter === 'published') {
        filtered = allClips.filter(c => c.human_verdict === 'PUBLISHED');
      } else if (currentFilter === 'safe') {
        filtered = allClips.filter(c => !c.is_nsfw && c.human_verdict !== 'PUBLISHED' && c.human_verdict !== 'FAILED' && c.human_verdict !== 'REJECTED_NSFW_TOMBSTONE' && c.video_path);
      } else if (currentFilter === 'nsfw') {
        filtered = allClips.filter(c => c.is_nsfw && c.human_verdict !== 'REJECTED_NSFW_TOMBSTONE' && c.video_path);
      }

      if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--text-muted); font-size: 13px;">No clips in this queue. Ingest a fresh clip to populate!</div>`;
        return;
      }

      filtered.forEach(clip => {
        const scoreClass = clip.virality_score >= 80 ? 'high' : (clip.virality_score >= 60 ? 'med' : 'low');
        const badgeTag = clip.is_nsfw ? `<span class="nsfw-badge">🔞 NSFW</span>` : `<span class="safe-badge">✅ SAFE</span>`;
        const cardClass = clip.virality_score >= 75 ? 'clip-card highlight' : 'clip-card';
        const isPub = clip.human_verdict === 'PUBLISHED';
        const isQueued = clip.human_verdict === 'QUEUED';
        const isFailed = clip.human_verdict === 'FAILED';

        let statusBadge = '';
        if (isPub) {
          statusBadge = `<span style="position:absolute; top:10px; left:10px; background:#00E676; color:#000; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; z-index:2;">LIVE 🚀</span>`;
        } else if (isQueued) {
          statusBadge = `<span style="position:absolute; top:10px; left:10px; background:#00F0FF; color:#000; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; z-index:2;">QUEUED 📥</span>`;
        } else if (isFailed) {
          statusBadge = `<span style="position:absolute; top:10px; left:10px; background:#FF2A6D; color:#fff; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; z-index:2;">FAILED ⚠️</span>`;
        }

        const failAlert = isFailed ? `
          <div style="background:#2A141D; border:1px solid #FF2A6D; color:#FF809B; padding:6px 8px; border-radius:6px; font-size:11px; margin-top:6px; line-height:1.3; word-break:break-word;">
            ⚠️ <strong>Error:</strong> ${clip.publish_error || 'Dispatch error occurred'}
          </div>
        ` : '';

        const card = document.createElement('div');
        card.className = cardClass;
        card.style.cursor = 'pointer';
        card.onclick = (e) => {
          if (!e.target.closest('button')) {
            openReviewModal(clip.clip_id);
          }
        };
        card.innerHTML = `
          <div class="video-wrap">
            <video src="${clip.video_path}" preload="none" muted playsinline onmouseenter="this.play()" onmouseleave="this.pause();this.currentTime=0;"></video>
            ${badgeTag}
            ${statusBadge}
            <div class="score-badge ${scoreClass}">★ ${clip.virality_score}</div>
          </div>
          <div class="clip-info">
            <div class="clip-title">${clip.target_search || clip.clip_id}</div>
            <div class="clip-meta-row">
              <span class="creator-pill">@${clip.creator || 'Streamer'}</span>
              <span>${clip.duration}s</span>
            </div>
            ${failAlert}
            <div style="display:flex; gap:8px; margin-top:10px;">
              <button class="btn-review-ok" style="flex:1;" onclick="openReviewModal('${clip.clip_id}')">
                <span>${isFailed ? '⚠️ Review Failure' : (isQueued ? '📥 Queued • Review' : (isPub ? '🚀 View Package' : '👁️ Review &amp; OK'))}</span>
              </button>
              <button class="btn-delete" title="Permanently delete clip" style="background:#2A141D; border:1px solid rgba(255,42,109,0.3); color:#FF2A6D; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px; transition:0.2s;" onmouseenter="this.style.background='#FF2A6D';this.style.color='#fff';" onmouseleave="this.style.background='#2A141D';this.style.color='#FF2A6D';" onclick="deleteClip('${clip.clip_id}', event)">
                <span>🗑️</span>
              </button>
            </div>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function renderStreams(streams) {
      const el = document.getElementById('stream-list');
      if (!streams || streams.length === 0) {
        el.innerHTML = '<div style="font-size:11px; color:var(--text-muted);">No live streams registered.</div>';
        return;
      }
      el.innerHTML = streams.map(s => `
        <div class="stream-item">
          <div class="stream-left">
            <span class="live-dot" style="background:${s.status.includes('LIVE') ? 'var(--green)' : 'var(--coral)'}; box-shadow:0 0 8px ${s.status.includes('LIVE') ? 'var(--green)' : 'var(--coral)'}"></span>
            <div>
              <div class="stream-name">${s.creator_name}</div>
              <div class="stream-plat">${s.language} • ${s.platform.toUpperCase()}</div>
            </div>
          </div>
          <a href="${s.stream_url}" target="_blank" style="font-size:11px; color:var(--cyan); text-decoration:none;">Watch ↗</a>
        </div>
      `).join('');
    }

    function renderTrends(trends) {
      const el = document.getElementById('trend-list');
      const list = trends.searches || [];
      if (list.length === 0) {
        el.innerHTML = '<div style="font-size:11px; color:var(--text-muted);">Mined 15m trends loading...</div>';
        return;
      }
      el.innerHTML = list.slice(0, 8).map(t => {
        const query = typeof t === 'string' ? t : (t.query || '');
        const vel = typeof t === 'string' ? '120' : (t.velocity_15m || '100');
        return `
        <div class="trend-item">
          <span class="trend-query">${query}</span>
          <span class="trend-vel">+${vel}%</span>
        </div>
      `}).join('');
    }

    function renderProps(props) {
      const el = document.getElementById('prop-list');
      if (!props || props.length === 0) {
        el.innerHTML = '<div style="font-size:11px; color:var(--text-muted);">Target props catalog loading...</div>';
        return;
      }
      el.innerHTML = props.slice(0, 5).map(p => {
        const title = p.name || p.title || 'Prop Target';
        const queries = (p.search_queries || []).slice(0, 2).join(' • ');
        return `
        <div class="prop-item">
          <div class="prop-title">${title}</div>
          <div class="prop-desc">${queries}</div>
        </div>
      `}).join('');
    }

    function openReviewModal(clipId) {
      const clip = allClips.find(c => c.clip_id === clipId);
      if (!clip) return;
      activeModalClip = clip;

      const pkg = clip.seo_package || {};
      document.getElementById('modal-video').src = clip.video_path;
      document.getElementById('modal-headline').innerText = clip.target_search || clip.clip_id;
      document.getElementById('modal-creator-tag').innerText = `Creator: @${clip.creator || 'Streamer'} (${clip.is_nsfw ? 'NSFW Censored' : 'Safe Gameplay'})`;

      document.getElementById('modal-yt-title').innerText = pkg.title || `💥 @${clip.creator} GTA 6 Showcase! #Shorts`;
      document.getElementById('modal-yt-desc').innerText = pkg.description || `⚡ ${clip.target_search}\n\n👤 Creator: @${clip.creator}\n🔥 Subscribe to @OutlawClips for high-octane GTA 6 moments!`;
      document.getElementById('modal-yt-tags').innerText = (pkg.youtube_tags || ['#GTA6', '#Shorts', '#OutlawClips']).join(' • ');

      document.getElementById('modal-ig-caption').innerText = pkg.instagram_caption || `💥 @${clip.creator} with unbelievable GTA 6 action!\n\n⚡ ${clip.target_search}\n👤 Creator: @${clip.creator}\n🔥 Follow @outlawclipshq for daily viral highlights!\n#GTA6 #GamingReels`;
      document.getElementById('modal-pinned-comment').innerText = pkg.pinned_comment || `🔥 Follow @outlawclipshq & drop a comment with your favorite streamer moment!`;

      const nsfwBar = document.getElementById('modal-nsfw-bar');
      if (nsfwBar) {
        nsfwBar.style.display = clip.is_nsfw ? 'flex' : 'none';
      }

      const failedBar = document.getElementById('modal-failed-bar');
      const failedMsg = document.getElementById('modal-failed-msg');
      if (failedBar && failedMsg) {
        if (clip.human_verdict === 'FAILED' && clip.publish_error) {
          failedMsg.innerText = clip.publish_error;
          failedBar.style.display = 'block';
        } else {
          failedBar.style.display = 'none';
        }
      }

      const qBtn = document.getElementById('modal-btn-queue');
      if (qBtn) {
        if (clip.human_verdict === 'FAILED') {
          qBtn.innerHTML = '🔁 Re-Queue for Dispatch';
        } else if (clip.human_verdict === 'QUEUED') {
          qBtn.innerHTML = '📥 In Dispatch Queue (Re-Queue)';
        } else if (clip.human_verdict === 'PUBLISHED') {
          qBtn.innerHTML = '📥 Re-Queue for Auto-Drop';
        } else {
          qBtn.innerHTML = '📥 Add to Dispatch Queue';
        }
      }

      const durElem = document.getElementById('modal-trim-current-dur');
      if (durElem) {
        durElem.innerText = `(${clip.duration || 30}s)`;
      }

      document.getElementById('review-modal').style.display = 'flex';
    }

    function closeReviewModal() {
      document.getElementById('modal-video').pause();
      document.getElementById('review-modal').style.display = 'none';
      activeModalClip = null;
    }

    function copyText(elemId) {
      const txt = document.getElementById(elemId).innerText;
      navigator.clipboard.writeText(txt);
      alert('Copied to clipboard!');
    }

    async function dispatchPublish(platform) {
      if (!activeModalClip) return;
      const btn = (typeof event !== 'undefined' && event) ? event.target : null;
      let originalText = '';
      if (btn) {
        originalText = btn.innerText;
        btn.innerText = '⏳ Publishing...';
        btn.disabled = true;
      }

      try {
        const res = await fetch('/api/publish_clip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            clip_id: activeModalClip.clip_id,
            platform: platform
          })
        }).then(r => r.json());

        if (res.status === 'ok') {
          let msg = `🎉 Dispatch Results:\n\n`;
          if (res.results && res.results.youtube) {
            msg += res.results.youtube.status === 'ok' 
              ? `✅ YouTube Short Published (Public): ${res.results.youtube.url}\n` 
              : `⚠️ YouTube: ${res.results.youtube.message}\n`;
          }
          if (res.results && res.results.instagram) {
            msg += res.results.instagram.status === 'ok' 
              ? `✅ Instagram Reel Published (Public): ${res.results.instagram.url}\n` 
              : `⚠️ Instagram: ${res.results.instagram.message}\n`;
          }
          alert(msg);
          closeReviewModal();
          loadData();
        } else {
          alert('Publish Notice: ' + (res.message || 'Error occurred during publish.'));
        }
      } catch (err) {
        alert('Publish request failed: ' + err);
      } finally {
        if (btn) {
          btn.innerText = originalText;
          btn.disabled = false;
        }
      }
    }

    async function deleteClip(clipId, ev) {
      if (ev) ev.stopPropagation();
      if (!confirm(`Are you sure you want to permanently delete clip '${clipId}'?`)) return;

      try {
        const res = await fetch('/api/delete_clip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clip_id: clipId })
        }).then(r => r.json());

        if (res.status === 'ok') {
          allClips = allClips.filter(c => c.clip_id !== clipId);
          renderClips();
          updateCounts();
        } else {
          alert('Delete failed: ' + (res.message || 'Unknown error'));
        }
      } catch (err) {
        alert('Delete request error: ' + err);
      }
    }

    async function deleteClipFromModal() {
      if (!activeModalClip) return;
      const cid = activeModalClip.clip_id;
      closeReviewModal();
      await deleteClip(cid);
    }

    async function queueClip(clipId, ev) {
      if (ev) ev.stopPropagation();
      try {
        const res = await fetch('/api/queue_clip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clip_id: clipId })
        }).then(r => r.json());

        if (res.status === 'ok') {
          const c = allClips.find(x => x.clip_id === clipId);
          if (c) {
            c.human_verdict = 'QUEUED';
            c.publish_error = '';
          }
          renderClips();
          updateCounts();
          alert('📥 Clip added to automated dispatch queue!');
        } else {
          alert('Queue error: ' + (res.message || 'Failed to queue'));
        }
      } catch (err) {
        alert('Queue request error: ' + err);
      }
    }

    async function queueActiveModalClip() {
      if (!activeModalClip) return;
      const cid = activeModalClip.clip_id;
      closeReviewModal();
      await queueClip(cid);
    }

    async function unblurClip(clipId, ev) {
      if (ev) ev.stopPropagation();
      if (!confirm(`Mark clip '${clipId}' as Safe and remove censor blur?`)) return;

      try {
        const res = await fetch('/api/unblur_clip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clip_id: clipId })
        }).then(r => r.json());

        if (res.status === 'ok') {
          alert('✅ ' + res.message);
          loadData();
        } else {
          alert('Error: ' + (res.message || 'Failed to unblur'));
        }
      } catch (err) {
        alert('Unblur request error: ' + err);
      }
    }

    async function recensorClip(clipId, ev) {
      if (ev) ev.stopPropagation();
      if (!confirm(`Re-render censor blur on '${clipId}' with the circular Outlaw Clips emblem?`)) return;

      try {
        const res = await fetch('/api/recensor_clip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clip_id: clipId })
        }).then(r => r.json());

        if (res.status === 'ok') {
          alert('✅ ' + res.message);
          loadData();
        } else {
          alert('Error: ' + (res.message || 'Failed to recensor'));
        }
      } catch (err) {
        alert('Recensor request error: ' + err);
      }
    }

    async function unblurActiveModalClip() {
      if (!activeModalClip) return;
      const cid = activeModalClip.clip_id;
      closeReviewModal();
      await unblurClip(cid);
    }

    async function recensorActiveModalClip() {
      if (!activeModalClip) return;
      const cid = activeModalClip.clip_id;
      closeReviewModal();
      await recensorClip(cid);
    }

    async function trimActiveModalClip(seconds) {
      if (!activeModalClip) return;
      if (!confirm(`Cut off the last ${seconds} seconds of this clip?`)) return;

      const btn3 = document.getElementById('btn-trim-3s');
      const btn5 = document.getElementById('btn-trim-5s');
      if (btn3) btn3.disabled = true;
      if (btn5) btn5.disabled = true;

      try {
        const res = await fetch('/api/trim_clip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            clip_id: activeModalClip.clip_id,
            trim_seconds: seconds
          })
        }).then(r => r.json());

        if (res.status === 'ok') {
          activeModalClip.duration = res.new_duration;
          const vid = document.getElementById('modal-video');
          if (vid) {
            vid.src = activeModalClip.video_path + '?t=' + Date.now();
            vid.play();
          }
          const durElem = document.getElementById('modal-trim-current-dur');
          if (durElem) durElem.innerText = `(${res.new_duration}s remaining)`;
          alert(`✂️ ${res.message}`);
          loadData();
        } else {
          alert('Trim Failed: ' + (res.message || 'Unknown error'));
        }
      } catch (err) {
        alert('Trim request error: ' + err);
      } finally {
        if (btn3) btn3.disabled = false;
        if (btn5) btn5.disabled = false;
      }
    }

    async function trimActiveModalClipCustom() {
      if (!activeModalClip) return;
      const input = prompt('Enter number of seconds to cut off from the end of this clip:', '3.5');
      if (!input) return;
      const sec = parseFloat(input);
      if (isNaN(sec) || sec <= 0) {
        alert('Please enter a valid positive number of seconds.');
        return;
      }
      await trimActiveModalClip(sec);
    }

    async function ingestFreshLiveClip() {
      const btn = document.querySelector('.btn-ingest');
      btn.innerText = '⏳ Ingesting...';
      btn.disabled = true;
      try {
        const res = await fetch('/api/fetch_live_gta6_clip', { method: 'POST' }).then(r => r.json());
        if (res.status === 'ok') {
          alert(`✅ Ingested fresh clip from @${res.creator} (Score: ${res.virality_score})`);
          loadData();
        } else {
          alert('Ingest message: ' + (res.message || 'No new clip'));
        }
      } catch (err) {
        alert('Ingest error: ' + err);
      } finally {
        btn.innerHTML = '<span>🔴 Ingest Live Clip</span>';
        btn.disabled = false;
      }
    }

    async function resetCacheAndDB() {
      if (!confirm("Are you sure you want to wipe all old cached clips and reset database to empty?")) return;
      try {
        const res = await fetch('/api/reset_cache_and_db', { method: 'POST' }).then(r => r.json());
        alert('✨ ' + res.message);
        loadData();
      } catch (err) {
        alert('Reset error: ' + err);
      }
    }

    loadData();
    document.addEventListener('DOMContentLoaded', loadData);
    setInterval(loadData, 30000);
  </script>
</body>
</html>
"""

class ClipperHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif path == "/api/training_clips":
            self._handle_api_training_clips()
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

        elif path == "/api/trends":
            self._handle_api_trends()
            return

        elif path == "/api/clips":
            self._handle_api_clips()
            return

        elif path == "/api/analytics":
            self._handle_api_analytics()
            return

        elif path.startswith("/video/"):
            rel_file = urllib.parse.unquote(path.replace("/video/", "")).strip("/")
            if not rel_file:
                self.send_error(404, "Invalid video path")
                return
            file_path = Path("output") / rel_file
            if file_path.is_file():
                self._serve_file(file_path, "video/mp4")
            else:
                self.send_error(404, "Video not found")
            return

        elif path.startswith("/training_candidates/") or path.startswith("/tournament_winners/"):
            rel_file = urllib.parse.unquote(path.lstrip("/")).strip("/")
            if not rel_file:
                self.send_error(404, "Invalid video path")
                return
            file_path = Path("output") / rel_file
            if file_path.is_file():
                self._serve_file(file_path, "video/mp4")
            else:
                self.send_error(404, "Video not found")
            return

        elif path == "/portal/ravi" or path == "/portal/ravi/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(RAVI_PORTAL_HTML.encode("utf-8"))
            return

        elif path == "/portal/api/ravi/clips":
            clips = get_ravi_candidate_clips()
            self._send_json({"clips": clips})
            return

        elif path == "/portal/api/ravi/journals":
            journal_dir = Path("docs/streams/ravi")
            sample_content = "No stream journal found."
            if journal_dir.exists():
                j_files = sorted(journal_dir.glob("*.md"), reverse=True)
                if j_files:
                    try:
                        sample_content = j_files[0].read_text(encoding="utf-8")
                    except Exception:
                        pass
            self._send_json({"sample": sample_content[:15000]})
            return

        elif path == "/portal/api/ravi/streams":
            self._send_json(get_stream_registry())
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if path == "/api/rate_clip":
            cid = payload.get("clip_id")
            stars = payload.get("stars", 5)
            verdict = payload.get("verdict", "APPROVED")
            critique = payload.get("critique", "")

            db_path = Path("data/telemetry.db")
            if db_path.exists() and cid:
                try:
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("""
                        UPDATE training_clip_ratings 
                        SET human_stars = ?, human_verdict = ?, human_critique = ?, rated_at = ?
                        WHERE clip_id = ?;
                    """, (stars, verdict, critique, time.time(), cid))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print("DB update error:", e)

            self._send_json({"status": "ok", "clip_id": cid, "stars": stars, "verdict": verdict})
            return

        elif path == "/api/publish_clip":
            cid = payload.get("clip_id")
            platform = payload.get("platform", "both")
            channel_type = payload.get("channel_type", "us")

            db_path = Path("data/telemetry.db")
            if not cid or not db_path.exists():
                self._send_json({"status": "error", "message": "Missing clip_id or database not found"})
                return

            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT clip_id, video_path, target_search, category, creator, expected_spoken, language, human_verdict FROM training_clip_ratings WHERE clip_id = ?", (cid,))
                row = c.fetchone()
                conn.close()

                if not row:
                    self._send_json({"status": "error", "message": f"Clip {cid} not found in database"})
                    return

                clip_id, vpath_raw, target_search, category, creator, spoken_tx, clip_language, human_verdict = row
                if category == "MATURE_SCENE" or human_verdict == "QUARANTINED":
                    self._send_json({"status": "error", "message": "Safety Guardrail Block: Quarantined mature scene. Cannot publish to public platforms."})
                    return

                # Automatic channel routing based on language
                clip_lang_str = (clip_language or "").lower()
                if "hindi" in clip_lang_str or "india" in clip_lang_str:
                    channel_type = "india"
                else:
                    channel_type = payload.get("channel_type", "us")

                rel_vpath = vpath_raw.replace("/video/", "")
                real_video_file = Path("output") / rel_vpath
                if not real_video_file.exists():
                    self._send_json({"status": "error", "message": f"Video file not found at {real_video_file}"})
                    return

                seo = ViralSEOEngine()
                seo_pkg = seo.generate_seo_package(
                    action_headline=target_search or clip_id,
                    transcript=spoken_tx or "",
                    streamer_name=creator or "Streamer",
                    channel_type=channel_type
                )

                pub = VideoPublisher()
                results = {}

                # YouTube Upload
                if platform in ["youtube", "both"]:
                    yt_res = pub.upload_youtube_unlisted(
                        video_path=str(real_video_file),
                        title=seo_pkg.get("title", f"{target_search} #Shorts"),
                        description=seo_pkg.get("description", ""),
                        tags=seo_pkg.get("youtube_tags", []),
                        target_channel=channel_type
                    )
                    results["youtube"] = yt_res

                # Instagram Upload
                if platform in ["instagram", "both"]:
                    ig_res = pub.upload_instagram_reel(
                        video_path=str(real_video_file),
                        caption=seo_pkg.get("instagram_caption", ""),
                        streamer_name=creator
                    )
                    results["instagram"] = ig_res

                # Check for platform upload failures
                has_error = False
                err_msgs = []
                if platform in ["youtube", "both"]:
                    yt_s = results.get("youtube", {}).get("status")
                    if yt_s != "ok":
                        has_error = True
                        err_msgs.append(f"YouTube: {results.get('youtube', {}).get('message', 'Upload error')}")
                if platform in ["instagram", "both"]:
                    ig_s = results.get("instagram", {}).get("status")
                    if ig_s != "ok":
                        has_error = True
                        err_msgs.append(f"Instagram: {results.get('instagram', {}).get('message', 'Upload error')}")

                conn = sqlite3.connect(str(db_path))
                if has_error:
                    full_err = " | ".join(err_msgs)
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'FAILED', publish_error = ? WHERE clip_id = ?", (full_err, cid))
                else:
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'PUBLISHED', publish_error = NULL WHERE clip_id = ?", (cid,))
                conn.commit()
                conn.close()

                self._send_json({
                    "status": "error" if has_error else "ok",
                    "clip_id": cid,
                    "has_error": has_error,
                    "message": " | ".join(err_msgs) if has_error else "Published successfully",
                    "results": results
                })
                return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/api/queue_clip":
            cid = payload.get("clip_id")
            db_path = Path("data/telemetry.db")
            if not cid or not db_path.exists():
                self._send_json({"status": "error", "message": "Missing clip_id"})
                return

            try:
                conn = sqlite3.connect(str(db_path))
                conn.execute("UPDATE training_clip_ratings SET human_verdict = 'QUEUED', publish_error = NULL WHERE clip_id = ?", (cid,))
                conn.commit()
                conn.close()
                self._send_json({"status": "ok", "clip_id": cid, "message": f"Clip '{cid}' added to automated dispatch queue!"})
                return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/api/unblur_clip":
            cid = payload.get("clip_id")
            db_path = Path("data/telemetry.db")
            if not cid or not db_path.exists():
                self._send_json({"status": "error", "message": "Missing clip_id"})
                return

            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT clip_id, video_path, expected_vision, creator, duration FROM training_clip_ratings WHERE clip_id = ?", (cid,))
                row = c.fetchone()
                if not row:
                    conn.close()
                    self._send_json({"status": "error", "message": f"Clip {cid} not found"})
                    return

                clip_id, vpath_raw, exp_vision, creator, dur = row
                slug = None
                if exp_vision and "[" in exp_vision and "]" in exp_vision:
                    slug = exp_vision.split("[")[1].split("]")[0].strip()

                rel_vpath = vpath_raw.replace("/video/", "")
                out_render = Path("output") / rel_vpath

                if slug:
                    import subprocess
                    ytdlp_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp"
                    raw_tmp = Path(f"/tmp/unblur_{slug}.mp4")
                    dl_cmd = [ytdlp_bin, f"https://clips.twitch.tv/{slug}", "-o", str(raw_tmp), "--force-overwrites"]
                    subprocess.run(dl_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if raw_tmp.exists():
                        slicer = VideoSlicer()
                        duration = min(float(dur or 24), 30.0)
                        slicer.slice_clip(
                            input_path=str(raw_tmp),
                            start_sec=0.0,
                            duration_sec=duration,
                            output_path=str(out_render),
                            tag_text="LIVE GTA",
                            brand_name="OUTLAW CLIPS",
                            creator_credit=creator or "Streamer",
                            censor_mode=None
                        )
                        raw_tmp.unlink(missing_ok=True)

                c.execute("UPDATE training_clip_ratings SET category = 'GAMEPLAY', human_verdict = 'REVIEW' WHERE clip_id = ?", (cid,))
                conn.commit()
                conn.close()

                self._send_json({"status": "ok", "clip_id": cid, "message": f"Clip '{cid}' marked Safe and unblurred!"})
                return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/api/recensor_clip":
            cid = payload.get("clip_id")
            db_path = Path("data/telemetry.db")
            if not cid or not db_path.exists():
                self._send_json({"status": "error", "message": "Missing clip_id"})
                return

            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT clip_id, video_path, expected_vision, creator, duration FROM training_clip_ratings WHERE clip_id = ?", (cid,))
                row = c.fetchone()
                if not row:
                    conn.close()
                    self._send_json({"status": "error", "message": f"Clip {cid} not found"})
                    return

                clip_id, vpath_raw, exp_vision, creator, dur = row
                slug = None
                if exp_vision and "[" in exp_vision and "]" in exp_vision:
                    slug = exp_vision.split("[")[1].split("]")[0].strip()

                rel_vpath = vpath_raw.replace("/video/", "")
                out_render = Path("output") / rel_vpath

                slicer = VideoSlicer()
                duration = min(float(dur or 24), 30.0)

                if slug:
                    import subprocess
                    ytdlp_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp"
                    raw_tmp = Path(f"/tmp/recensor_{slug}.mp4")
                    dl_cmd = [ytdlp_bin, f"https://clips.twitch.tv/{slug}", "-o", str(raw_tmp), "--force-overwrites"]
                    subprocess.run(dl_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if raw_tmp.exists():
                        slicer.slice_clip(
                            input_path=str(raw_tmp),
                            start_sec=0.0,
                            duration_sec=duration,
                            output_path=str(out_render),
                            tag_text="LIVE GTA",
                            brand_name="OUTLAW CLIPS",
                            creator_credit=creator or "Streamer",
                            censor_mode="circular_logo"
                        )
                        raw_tmp.unlink(missing_ok=True)
                elif out_render.exists():
                    slicer.apply_dynamic_motion_censor(
                        video_path=str(out_render),
                        censor_mode="circular_logo",
                        brand_name="OUTLAW CLIPS"
                    )

                c.execute("UPDATE training_clip_ratings SET category = 'MATURE_SCENE', human_verdict = 'REVIEW' WHERE clip_id = ?", (cid,))
                conn.commit()
                conn.close()

                self._send_json({"status": "ok", "clip_id": cid, "message": f"Circular emblem censor applied to '{cid}'!"})
                return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/api/trim_clip":
            cid = payload.get("clip_id")
            trim_seconds = float(payload.get("trim_seconds", 3.0))
            db_path = Path("data/telemetry.db")
            if not cid or not db_path.exists():
                self._send_json({"status": "error", "message": "Missing clip_id"})
                return

            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT clip_id, video_path, duration FROM training_clip_ratings WHERE clip_id = ?", (cid,))
                row = c.fetchone()
                if not row:
                    conn.close()
                    self._send_json({"status": "error", "message": f"Clip {cid} not found"})
                    return

                clip_id, vpath_raw, dur = row
                rel_vpath = vpath_raw.replace("/video/", "")
                out_render = Path("output") / rel_vpath
                if not out_render.exists():
                    conn.close()
                    self._send_json({"status": "error", "message": f"Video file not found at {out_render}"})
                    return

                import cv2, subprocess, shutil
                cap = cv2.VideoCapture(str(out_render))
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                curr_duration = frame_count / fps if fps > 0 else float(dur or 30.0)
                cap.release()

                new_duration = curr_duration - trim_seconds
                if new_duration < 5.0:
                    conn.close()
                    self._send_json({"status": "error", "message": f"Cannot trim clip to less than 5s (current: {curr_duration:.1f}s, requested trim: {trim_seconds}s)"})
                    return

                # Backup before trimming
                orig_backup = out_render.with_suffix(out_render.suffix + ".orig")
                if not orig_backup.exists():
                    shutil.copy(str(out_render), str(orig_backup))

                temp_trimmed = out_render.parent / f"temp_trim_{out_render.name}"
                ffmpeg_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/ffmpeg" if Path("/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/ffmpeg").exists() else "ffmpeg"

                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(out_render),
                    "-t", str(new_duration),
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "20",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    str(temp_trimmed)
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                if temp_trimmed.exists() and temp_trimmed.stat().st_size > 1000:
                    temp_trimmed.replace(out_render)
                    c.execute("UPDATE training_clip_ratings SET duration = ? WHERE clip_id = ?", (round(new_duration, 1), cid))
                    conn.commit()
                    conn.close()
                    self._send_json({
                        "status": "ok",
                        "clip_id": cid,
                        "new_duration": round(new_duration, 1),
                        "message": f"Successfully trimmed {trim_seconds}s! New duration: {round(new_duration, 1)}s"
                    })
                    return
                else:
                    conn.close()
                    self._send_json({"status": "error", "message": "FFmpeg trimming failed to generate valid video"})
                    return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/api/delete_clip":
            cid = payload.get("clip_id")
            db_path = Path("data/telemetry.db")
            if not cid or not db_path.exists():
                self._send_json({"status": "error", "message": "Missing clip_id or database not found"})
                return

            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS tombstone_rejected_clips (slug TEXT PRIMARY KEY, title TEXT, clip_id TEXT, rejected_at REAL);")
                c.execute("SELECT video_path, expected_vision, target_search FROM training_clip_ratings WHERE clip_id = ?", (cid,))
                row = c.fetchone()
                if row:
                    vpath_raw, exp_vision, target_search = row
                    
                    # Extract unique Twitch slug or clip identifier
                    slug = cid
                    if exp_vision and "[" in exp_vision and "]" in exp_vision:
                        slug = exp_vision.split("[")[1].split("]")[0].strip()
                    elif cid.startswith("gta6_twitch_"):
                        parts = cid.split("_")
                        if len(parts) >= 3:
                            slug = parts[2]

                    c.execute("""
                        INSERT OR REPLACE INTO tombstone_rejected_clips (slug, title, clip_id, rejected_at)
                        VALUES (?, ?, ?, ?);
                    """, (slug, target_search or cid, cid, time.time()))

                    if vpath_raw:
                        vpath_clean = vpath_raw.replace("/video/", "")
                        target_file = Path("output") / vpath_clean
                        target_file.unlink(missing_ok=True)
                        target_file.with_suffix(".jpg").unlink(missing_ok=True)
                        target_file.with_suffix(".thumb.jpg").unlink(missing_ok=True)
                        orig_file = target_file.parent / f"{target_file.name}.orig"
                        orig_file.unlink(missing_ok=True)

                c.execute("DELETE FROM training_clip_ratings WHERE clip_id = ?", (cid,))
                conn.commit()
                conn.close()

                self._send_json({"status": "ok", "clip_id": cid, "message": f"Clip {cid} permanently blacklisted and deleted."})
                return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/api/reset_cache_and_db":
            try:
                from scripts.reset_cache_and_db import reset_all
                reset_all()
                self._send_json({"status": "ok", "message": "All cache & database wiped clean! Ready for fresh clips."})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
            return

        elif path == "/api/fetch_live_gta6_clip":
            try:
                ts = int(time.time())
                clip_id = f"live_gta6_{ts}"

                twitch_engine = TwitchClipEngine(temp_dir="downloads/ring_buffer/gta6_live")
                twitch_clips = []
                for gname in ["Grand Theft Auto VI"]:
                    for period in ["LAST_DAY", "LAST_WEEK"]:
                        try:
                            found = twitch_engine.fetch_top_clips(game_name=gname, limit=15, period=period)
                            for f in found:
                                if not any(existing["slug"] == f["slug"] for existing in twitch_clips):
                                    twitch_clips.append(f)
                        except Exception:
                            pass
                
                db_path = Path("data/telemetry.db")
                all_text = ""
                recent_creators = []
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("CREATE TABLE IF NOT EXISTS tombstone_rejected_clips (slug TEXT PRIMARY KEY, title TEXT, clip_id TEXT, rejected_at REAL);")
                    c.execute("""
                        SELECT clip_id, expected_vision, target_search FROM training_clip_ratings
                        UNION
                        SELECT clip_id, slug, title FROM tombstone_rejected_clips;
                    """)
                    all_text = " ".join(str(val).lower() for row in c.fetchall() for val in row if val)
                    c.execute("SELECT creator FROM training_clip_ratings ORDER BY rated_at DESC LIMIT 5;")
                    recent_creators = [r[0] for r in c.fetchall() if r[0]]
                    conn.close()

                unprocessed = [
                    tc for tc in twitch_clips 
                    if tc["title"].lower().strip() not in all_text and tc["slug"].lower()[:15] not in all_text
                ]
                
                # Creator diversity anti-repetition filter
                diversified = [tc for tc in unprocessed if tc.get("channel") not in recent_creators[:2]]
                candidate_pool = diversified if diversified else unprocessed

                if candidate_pool:
                    chosen_clip = candidate_pool[0]
                    creator = chosen_clip.get("channel", "LiveStreamer")
                    clip_slug = chosen_clip["slug"]
                    video_url = chosen_clip.get("url") or f"https://clips.twitch.tv/{clip_slug}"
                    raw_mp4 = twitch_engine.download_clip(video_url, output_name=f"{clip_id}_raw.mp4")

                    if raw_mp4 and Path(raw_mp4).exists():
                        transcriber = Transcriber()
                        tx_res = transcriber.transcribe(str(raw_mp4))
                        transcript = " ".join(s.get("text", "") for s in tx_res).strip()
                        if not transcript:
                            transcript = f"{creator} executing intense high speed GTA chase maneuver"

                        scorer = ViralityScorer()
                        score_data = scorer.score_transcript(transcript, streamer_name=creator)
                        virality_score = score_data.get("virality_score", 85.0)

                        out_render = Path(f"output/training_candidates/{clip_id}.mp4")
                        out_render.parent.mkdir(parents=True, exist_ok=True)
                        gatekeeper = SemanticGatekeeper()
                        v_res = gatekeeper.check_video_visual_nsfw(str(raw_mp4), threshold=0.55)
                        is_mature = v_res.get("is_nsfw", False)
                        category = "MATURE_SCENE" if is_mature else "GAMEPLAY"
                        verdict = "QUARANTINED" if is_mature else "REVIEW"
                        censor_mode = "broadcast_mosaic" if is_mature else None

                        slicer = VideoSlicer()
                        duration = min(float(chosen_clip.get("duration", 24)), 30.0)
                        slicer.slice_clip(
                            input_path=str(raw_mp4),
                            start_sec=0.0,
                            duration_sec=duration,
                            output_path=str(out_render),
                            tag_text="LIVE GTA",
                            brand_name="OUTLAW CLIPS",
                            creator_credit=creator,
                            censor_mode=censor_mode
                        )
                        raw_mp4.unlink(missing_ok=True)

                        conn = sqlite3.connect(str(db_path))
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO training_clip_ratings 
                            (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, virality_score, human_stars, human_verdict, human_critique, rated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 5, ?, '', ?);
                        """, (
                            clip_id,
                            f"/video/training_candidates/{clip_id}.mp4",
                            chosen_clip['title'],
                            category,
                            "Live / English",
                            f"@{creator}",
                            creator,
                            transcript[:200],
                            f"Audience Clip [{clip_slug}]",
                            duration,
                            virality_score,
                            verdict,
                            float(ts)
                        ))
                        conn.commit()
                        conn.close()

                        self._send_json({
                            "status": "ok",
                            "clip_id": clip_id,
                            "creator": creator,
                            "virality_score": virality_score
                        })
                        return

                self._send_json({"status": "error", "message": "No new unprocessed clips found at this moment."})
                return
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
                return

        elif path == "/portal/api/ravi/feedback":
            res = submit_ravi_feedback(payload)
            self._send_json(res)
            return

        elif path == "/portal/api/ravi/query":
            q = payload.get("query", "")
            matches = search_stream_journals(q)
            self._send_json(matches)
            return

        elif path == "/portal/api/ravi/rescan":
            res = rescan_stream(payload)
            self._send_json(res)
            return

        elif path == "/portal/api/ravi/snip":
            res = snip_moment(payload)
            self._send_json(res)
            return

        self.send_error(404, "Not Found")

    def _serve_file(self, file_path: Path, mime: str):
        try:
            chunk_size = 64 * 1024
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()

            with open(file_path, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    self.wfile.write(data)
        except Exception:
            pass

    def _handle_api_training_clips(self):
        db_path = Path("data/telemetry.db")
        clips = []

        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("""
                    SELECT clip_id, video_path, target_search, category, language, channel, creator, duration, virality_score, human_stars, human_verdict, human_critique, publish_error 
                    FROM training_clip_ratings 
                    WHERE human_verdict NOT IN ('REJECTED_NSFW_TOMBSTONE', 'DELETED')
                    ORDER BY 
                        rated_at DESC, 
                        rowid DESC;
                """)
                for r in c.fetchall():
                    raw_vpath = r[1] or ""
                    clean_vpath = (
                        (raw_vpath if raw_vpath.startswith("/video/") else f"/video/{raw_vpath.lstrip('/')}")
                        if raw_vpath else ""
                    )
                    if clean_vpath:
                        rel_check = clean_vpath.replace("/video/", "").strip("/")
                        if not (Path("output") / rel_check).is_file():
                            clean_vpath = ""
                    score = r[8] if r[8] is not None and r[8] > 0 else float((r[9] or 4) * 20.0)
                    category = r[3] or "GAMEPLAY"
                    is_nsfw = (category == "MATURE_SCENE")
                    creator = r[6] or "Streamer"
                    title = r[2] or r[0].replace("_", " ").title()

                    seo_pkg = {
                        "title": f"🔥 {title} #Shorts" if "#Shorts" not in title else title,
                        "description": f"⚡ {title}\n\n👤 Creator: @{creator}\n🔥 Subscribe to @OutlawClipsGlobal for high-octane GTA 6 moments!",
                        "youtube_tags": ["GTA 6", "GTA VI", "Gaming", "Shorts", f"{creator} Clips", "OutlawClips"],
                        "instagram_caption": f"💥 @{creator} with unbelievable GTA 6 action!\n\n⚡ {title}\n👤 Creator: @{creator}\n🔥 Follow @outlawclipshq for daily viral highlights!\n#GTA6 #GamingReels",
                        "pinned_comment": f"🔥 Follow @outlawclipshq & drop a comment with your favorite moment!"
                    }

                    clips.append({
                        "clip_id": r[0],
                        "video_path": clean_vpath,
                        "target_search": title,
                        "category": category,
                        "is_nsfw": is_nsfw,
                        "language": r[4],
                        "channel": r[5],
                        "creator": creator,
                        "duration": r[7] or 25.0,
                        "virality_score": score,
                        "human_stars": r[9] or 4,
                        "human_verdict": r[10] or "UNRATED",
                        "human_critique": r[11] or "",
                        "publish_error": r[12] or "",
                        "seo_package": seo_pkg
                    })
                conn.close()
            except Exception as e:
                print("Error loading clips:", e)

        self._send_json(clips)

    def _handle_api_stats(self):
        db_path = Path("data/telemetry.db")
        total_clips = 0
        review_count = 0
        nsfw_count = 0

        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT COUNT(*), SUM(CASE WHEN human_stars >= 4 THEN 1 ELSE 0 END), SUM(CASE WHEN category = 'MATURE_SCENE' THEN 1 ELSE 0 END) FROM training_clip_ratings;")
                row = c.fetchone()
                total_clips = row[0] or 0
                review_count = row[1] or 0
                nsfw_count = row[2] or 0
                conn.close()
            except Exception:
                pass

        self._send_json({
            "total_clips": total_clips,
            "review_count": review_count,
            "nsfw_count": nsfw_count
        })

    def _handle_api_analytics(self):
        try:
            from src.social_analytics import SocialAnalyticsEngine
            analytics = SocialAnalyticsEngine()
            data = analytics.get_all_metrics()
            self._send_json(data)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)})

    def _handle_api_streams(self):
        streams = [
            {"session_id": "stream_rockstar", "creator_name": "Rockstar Games Official", "platform": "youtube", "stream_url": "https://www.youtube.com/@RockstarGames", "language": "English (Global)", "status": "LIVE & VERIFIED"},
            {"session_id": "stream_xyaa", "creator_name": "Xyaa Live", "platform": "youtube", "stream_url": "https://www.youtube.com/@xyaalive", "language": "Hindi / English", "status": "LIVE & VERIFIED"},
            {"session_id": "stream_techno", "creator_name": "Techno Gamerz", "platform": "youtube", "stream_url": "https://www.youtube.com/@TechnoGamerzOfficial", "language": "Hindi (India)", "status": "LIVE & VERIFIED"},
            {"session_id": "stream_radbrad", "creator_name": "theRadBrad", "platform": "youtube", "stream_url": "https://www.youtube.com/@theRadBrad", "language": "English (Global)", "status": "LIVE & VERIFIED"},
            {"session_id": "stream_twitch", "creator_name": "Twitch GTA 6 Top Streamers", "platform": "twitch", "stream_url": "https://www.twitch.tv/directory/category/grand-theft-auto-vi", "language": "Global Multi", "status": "LIVE & VERIFIED"}
        ]
        self._send_json(streams)

    def _handle_api_props(self):
        en_p = Path("data/properties_english.json")
        props = []
        if en_p.exists():
            try:
                with open(en_p, "r") as f:
                    props = json.load(f).get("properties", [])
            except Exception:
                pass
        self._send_json(props)

    def _handle_api_trends(self):
        trends_p = Path("data/top_50_live_gta6_searches.json")
        if trends_p.exists():
            try:
                with open(trends_p, "r") as f:
                    data = json.load(f)
                self._send_json(data)
                return
            except Exception:
                pass
        self._send_json({"total": 0, "searches": []})

    def _handle_api_clips(self):
        self._handle_api_training_clips()

    def _send_json(self, data: Any):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
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
    httpd = None
    target_ports = [port, 8765, 8766]
    for p in target_ports:
        try:
            DualStackHTTPServer.address_family = socket.AF_INET
            httpd = DualStackHTTPServer(("0.0.0.0", p), ClipperHTTPHandler)
            port = p
            break
        except Exception:
            try:
                DualStackHTTPServer.address_family = socket.AF_INET6
                httpd = DualStackHTTPServer(("::", p), ClipperHTTPHandler)
                port = p
                break
            except Exception:
                continue

    if not httpd:
        raise RuntimeError("Could not bind HTTP server to any available port.")

    print(f"🚀 Outlaw Clips Command Hub running at: http://0.0.0.0:{port} (http://localhost:{port})")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
