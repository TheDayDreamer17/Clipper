#!/usr/bin/env bash
# ==============================================================================
# VS Code Remote Tunnel Launcher for Ravi (@ravoop)
# Runs on your Mac to allow Ravi to code, run Python & FFmpeg directly from Windows
# ==============================================================================

WORKTREE_DIR="/Users/vismaythaker/workspace/projects/Clipper-ravi"

echo "=================================================================="
echo "🚀 Clipper Remote Compute Node (Apple Silicon M-Series)"
echo "📂 Ravi's Isolated Worktree: $WORKTREE_DIR"
echo "🌿 Dedicated Git Branch:     ravi-pipeline"
echo "🐍 Shared Python Virtualenv: $WORKTREE_DIR/.venv"
echo "🎬 Shared Candidate Cuts:    $WORKTREE_DIR/output/training_candidates"
echo "=================================================================="
echo ""
echo "Starting secure tunnel..."
echo "Follow the 1-time GitHub authentication prompt if prompted."
echo ""

code tunnel --accept-server-license-terms
