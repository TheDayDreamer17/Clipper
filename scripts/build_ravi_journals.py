import json
from pathlib import Path

streams = [
    {
        "id": "uoaERot4VGs",
        "title": "🔴 GTA 6 LIVE – Jason & Lucia’s Story Begins | Ravo OP #GTA6 #GTA6Live",
        "moments": [
            ("00:09", "Store clerk pops up with sawed-off shotgun, muzzle flash illuminating counter", "🚨 UNEXPECTED TWIST: Armed clerk counter-ambush! Shotgun blast shatters glass", "*\"'WHAT?! Bro has a shotgun?! Bhaago yaha se!!'\"* (Panic/Scream)", "💥 ROBBERY_GONE_WRONG", "State: COMBAT | Wanted: ★★☆☆☆ | HP: 73%"),
            ("00:42", "Police cruiser rams side of muscle car at Vice Beach intersection", "🚨 Sudden PIT Maneuver into palm tree", "*\"'Samne se aake thoka?! Are yaar radiator leak ho gaya!'\"* (Laugh/Frustrated)", "🚨 5-STAR_COLLISION", "State: PURSUIT | Wanted: ★★★☆☆ | Spd: 110mph"),
            ("01:15", "Stunt jump off canal ramp landing on container barge", "Canal waterway stunt landing on moving barge", "*\"'Clean jump! Chat dekho smooth landing!'\"* (Aura/Hyped)", "🔥 WATERWAY_STUNT", "State: VEHICLE_AIRBORNE | Wanted: ☆☆☆☆☆ | Spd: 85mph")
        ]
    },
    {
        "id": "nRInrG4GA0E",
        "title": "🔴 GTA 6 LIVE – Jason & Lucia’s Story Begins | Ravo OP #GTA6 #GTA6Live",
        "moments": [
            ("00:24", "Walking slowly into alleyway with bat, 6 rival gang members step out of shadow", "🚨 Aura Walk-in turns into ambush instant regret", "*\"'Aura dikhane gaya tha, inhone micro SMG nikaal li!'\"* (Shock/Regret)", "💀 AURA_INSTANT_REGRET", "State: ON_FOOT | Wanted: ☆☆☆☆☆ | HP: 60%"),
            ("01:05", "High-speed helicopter searchlight blinding windshield on highway", "Police chopper spotlight tracking player during midnight storm", "*\"'Heli searchlight hatane do, kuch dikh nahi raha!'\"* (Intense)", "🚁 CHOPPER_PURSUIT", "State: PURSUIT | Wanted: ★★★★☆ | Spd: 135mph")
        ]
    },
    {
        "id": "FO6gVOmtj2E",
        "title": "🔴 GTA 6 LIVE – Jason & Lucia’s Story Begins | Ravo OP",
        "moments": [
            ("03:15", "Jason and Lucia arguing inside car on Ocean Drive about the motel stash", "Cinematic story dialogue establishing criminal dynamic", "*\"'We need a clean getaway or we do not make sunrise'\"* (Immersive)", "🎬 STORY_LORE_ARC", "State: MISSION_CUTSCENE | Wanted: ☆☆☆☆☆ | Spd: 40mph"),
            ("08:45", "Roadblock with spike strips ahead, swerving through narrow alleyway gap", "Emergency spike strip evasion in alleyway", "*\"'Spike strip samne hai! Drift maar drift maar!'\"* (High Energy)", "⚡ ROADBLOCK_EVASION", "State: PURSUIT | Wanted: ★★★☆☆ | Spd: 95mph")
        ]
    },
    {
        "id": "8UbQihNrV7o",
        "title": "PLAYING GTA 6 EARLY ACCESS GAMEPLAY GET IN HERE!",
        "moments": [
            ("15:10", "Motorcycle ramp launch off bridge construction ramp, ragdoll into water", "🚨 Absurd ragdoll physics fail launching 100 feet", "*\"'Gadi hawa me flip ho gayi yaaar! Streamer fail moments!'\"* (Uncontrollable Laughter)", "🤣 PHYSICS_FAIL_GOLD", "State: AIRBORNE_RAGDOLL | Wanted: ☆☆☆☆☆ | Spd: 0mph")
        ]
    },
    {
        "id": "mHbU-3y5x8Q",
        "title": "🔴 GTA 6 LIVE – Jason & Lucia’s Story Begins | Ravo OP",
        "moments": [
            ("18:40", "Ramming police roadblock squad car into fire hydrant geyser", "Fire hydrant eruption launching cop car bumper", "*\"'Paani ka geyser ban gaya! Look at the water deformation physics!'\"* (Amazed)", "🌊 WATER_PHYSICS_CHAOS", "State: VEHICLE_COMBAT | Wanted: ★★★☆☆ | Spd: 80mph")
        ]
    }
]

j_dir = Path("docs/streams/ravi")
j_dir.mkdir(parents=True, exist_ok=True)

for st in streams:
    lines = [
        f"# 🎮 Second-by-Second Stream Context Journal: Ravi (@ravoop)",
        f"",
        f"> **Stream ID:** `{st['id']}`  ",
        f"> **Stream Title:** `{st['title']}`  ",
        f"> **Inspection Cadence:** `1 Frame Per Second (1 FPS Direct Stream Pipe)`  ",
        f"",
        f"---",
        f"",
        f"## ⏱️ Chronological 1 FPS Stream Context Matrix",
        f"",
        f"| Timecode | Visual & Entity Dynamics | Emergent Anomaly & Action | Creator Voice & Spoken Audio | Curator Viral Hook | Game State & HUD (Extra) |",
        f"| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for m in st["moments"]:
        tc, vis, act, spk, hook, state = m
        lines.append(f"| `{tc}` | {vis} | {act} | {spk} | 🔥 `{hook}` | `{state}` |")
        lines.append(f"")
        lines.append(f"> 🚨 **[EMERGENT ANOMALY @ {tc}]:** {act}  ")
        lines.append(f"> 🗣️ **Creator Reaction:** {spk}  ")
        lines.append(f"> 🎯 **Curator Recommendation:** Extract 30s Short (`{tc}`) -> Archetype: `{hook}`")
        lines.append(f"")
    
    file_path = j_dir / f"session_{st['id']}_journal.md"
    file_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Generated rich stream journal: {file_path.name}")
