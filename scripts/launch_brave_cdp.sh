#!/bin/bash
# Launch your everyday Brave Browser with Chrome DevTools Protocol (CDP) enabled on port 9222.
# This allows Clipper agents to connect directly to your live, logged-in session.

echo "🚀 Launching Brave with CDP on port 9222..."
open -a "Brave Browser" --args --remote-debugging-port=9222
echo "✅ Brave launched. CDP endpoint active at http://127.0.0.1:9222"
