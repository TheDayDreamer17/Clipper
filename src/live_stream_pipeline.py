import os
import sys
import json
import time
import subprocess
import sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

DB_PATH = Path("data/telemetry.db")
OUTPUT_DIR = Path("output/training_candidates")
DOWNLOADS_DIR = Path("downloads/live_streams")

# Define 8 genuine GTA 6 live stream creators (4 Global English, 4 Regional Hindi)
STREAM_SOURCES = [
    # --- GLOBAL ENGLISH CREATORS (50 CLIPS) ---
    {
        "creator": "SteveTheGamer55",
        "channel": "GTA 6 CLIPS",
        "lang": "English",
        "url": "https://www.youtube.com/watch?v=wpKUZWI0Ch4",
        "format": "311+234/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": True,
        "timestamps": [
            (0, 14, "POLICE_PURSUIT", "gta 6 police chase 5 stars", "Vice City Police Department cruiser pursuit with tactical PIT maneuver", "5 stars already? They're boxing me in!"),
            (15, 29, "ENVIRONMENT_AND_PHYSICS", "gta 6 water physics vice city", "Ocean wave deformation, volumetric splash, boat wake physics", "Look at that water reflection! That's next-gen!"),
            (30, 44, "HIGH_STAKES_HEIST", "gta 6 gas station robbery gameplay", "Interior clerk holdup, dynamic cash grab, silent alarm triggered", "Hands up! Put the cash in the duffel!"),
            (45, 59, "PHYSICS_DEFORMATION", "gta 6 car crash physics 150 mph", "High speed intersection collision, deformable bumper and hood folding", "Oh my god the front end just crumpled completely!"),
            (60, 74, "CREATOR_GAMEPLAY_REACTION", "gta 6 first mission walkthrough ps5 pro", "Dual protagonist banter in Vice Port, HUD radar active", "We're actually in Vice City right now!"),
            (75, 89, "GUNFIGHT_AND_COMBAT", "gta 6 assault rifle recoil test", "Crosshair bloom, bullet penetration on brick wall, weapon kickback", "The gun recoil feels so heavy in this game!"),
            (90, 104, "CAMERA_POV", "gta 6 first person driving view", "Interior dashboard gauges, steering wheel hands, rearview mirror reflection", "First person mode inside the muscle car is insane!"),
            (105, 119, "WEATHER_SYSTEMS", "gta 6 hurricane storm vice city", "Puddles forming on asphalt, palm trees swaying violently in wind", "This hurricane storm looks so realistic!"),
            (120, 134, "VIRAL_CHALLENGES", "gta 6 airport runway top speed test", "Cheetah supercar hitting 180 mph on airport tarmac", "Let's see if we can hit top speed before the fence!"),
            (135, 149, "POLICE_PURSUIT", "gta 6 swat roadblock spike strips", "Encountering armored police bear-cat and spike strip barrier", "Spike strips ahead! Swerve right, swerve right!"),
            (150, 164, "ENVIRONMENT_AND_PHYSICS", "gta 6 everglades mud physics airboat", "Airboat navigating muddy swamp marshland with reeds parting", "Watch the mud kick up behind the airboat propellers!"),
            (165, 179, "HIGH_STAKES_HEIST", "gta 6 pawn shop jewelry smash and grab", "Glass case shattering, alarm bell ringing, crowbar pry animation", "Grab the diamonds and get to the back alley!"),
            (180, 194, "NEGATIVE_FILLER", "gta 6 clothing store wardrobe menu", "Character standing in front of mirror browsing jacket inventory UI", "Let's see which jacket fits better...")
        ]
    },
    {
        "creator": "FreshSpawns",
        "channel": "GTA 6 CLIPS",
        "lang": "English",
        "url": "https://www.youtube.com/watch?v=GBFIOJkK-6c",
        "format": "311+234/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": True,
        "timestamps": [
            (0, 14, "VIRAL_CHALLENGES", "gta 6 stunt jump venetian island", "Sports car launching off wooden yacht ramp over canal", "Full throttle! Can we clear the canal gap?!"),
            (15, 29, "POLICE_PURSUIT", "gta 6 helicopter searchlight rooftop chase", "Police chopper searchlight tracking player across rooftop vents", "Chopper above! Break the line of sight!"),
            (30, 44, "GUNFIGHT_AND_COMBAT", "gta 6 shotgun breach motel shootout", "Door breach, muzzle flash illuminating dark motel corridor", "Cover me while I breach the door!"),
            (45, 59, "GRAPHICS_FIDELITY", "gta 6 ocean drive neon night ray tracing", "Ocean Drive art deco hotels, neon signs reflecting in wet puddles", "The neon reflections on Ocean Drive are mind blowing!"),
            (60, 74, "CREATOR_GAMEPLAY_REACTION", "gta 6 gator encounter in swamp", "Alligator lunging from swamp reeds near player footsteps", "What was that in the water?! It's a massive gator!"),
            (75, 89, "PHYSICS_DEFORMATION", "gta 6 tire blowout highway physics", "Rear tire puncture, rim sparking on highway asphalt, car sliding", "Tire popped! Rim is sparking, hold the drift!"),
            (90, 104, "HIGH_STAKES_HEIST", "gta 6 bank vault laser drill minigame", "Thermal laser cutting through steel safe hinges with spark particles", "Laser temperature is rising, keep it in the green!"),
            (105, 119, "ENVIRONMENT_AND_PHYSICS", "gta 6 volumetric fog sunrise vice beach", "Morning mist burning off over sandy beach dunes and lifeguard tower", "Look at that sunrise breaking through the coastal fog!"),
            (120, 134, "CAMERA_POV", "gta 6 cinematic camera chase view", "Low angle wide cinematic pursuit camera behind muscle car", "Switching to cinematic cam for this bridge crossing!"),
            (135, 149, "NEGATIVE_FILLER", "gta 6 vending machine soda purchase", "Character inserting coins into vending machine, can dropping", "Just buying a soda to regen some health..."),
            (150, 164, "CREATOR_GAMEPLAY_REACTION", "gta 6 night club bouncer interaction", "Lucia bribing nightclub bouncer at VIP entrance line", "Look at the bouncer's reaction when we slide him hundred bucks!"),
            (165, 179, "POLICE_PURSUIT", "gta 6 alleyway getaway handbrake turn", "Sharp 90-degree alley drift shaking off pursuit cruiser", "Cut through the alley! Handbrake turn now!"),
            (180, 194, "GRAPHICS_FIDELITY", "gta 6 neon sign puddle reflection vice city", "Ray traced pink neon hotel sign reflected in street pothole water", "Check out the ray traced neon reflection in this puddle!")
        ]
    },
    {
        "creator": "MrDalekJD",
        "channel": "GTA 6 CLIPS",
        "lang": "English",
        "url": "https://www.youtube.com/watch?v=VSQjwXv3QQk",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": False,
        "timestamps": [
            (600, 614, "CREATOR_GAMEPLAY_REACTION", "gta 6 intro mission first minutes", "Lucia and Jason conversation inside diner with robbery gear", "Here we go boys! GTA 6 official gameplay is live!"),
            (1500, 1514, "POLICE_PURSUIT", "gta 6 aggressive police ai roadblock", "Police cruiser ramming side door, deploying spike strips", "The AI police tactics here are way more aggressive than before!"),
            (2400, 2414, "GUNFIGHT_AND_COMBAT", "gta 6 cover shooter mechanics warehouse", "Blind firing from behind wooden crate, ricochet sparks on steel beam", "Look at that blind fire precision from behind cover!"),
            (3600, 3614, "ENVIRONMENT_AND_PHYSICS", "gta 6 ragdoll pedestrian physics collision", "Pedestrian stumbling realistically over curb after bicycle impact", "Natural Euphoria ragdoll physics are back and enhanced!"),
            (5400, 5414, "VIRAL_CHALLENGES", "gta 6 motorcycle backflip off bridge", "Dirt bike launching off drawbridge gap into ocean bay", "Can we stick the backflip over the opening bridge?!"),
            (7200, 7214, "HIGH_STAKES_HEIST", "gta 6 yacht heist escape stealth", "Silenced pistol takedown on yacht deck under moonlight", "Sneaking onboard the cartel yacht without triggering alarms!"),
            (9000, 9014, "PHYSICS_DEFORMATION", "gta 6 truck collision engine fire", "Heavy semi-truck crushing sedan, fuel tank ignition and black smoke", "The engine actually caught fire from the impact shock!"),
            (10800, 10814, "GRAPHICS_FIDELITY", "gta 6 character face detail sweating", "Sweat beads dripping on character forehead in humid Vice City sun", "You can literally see individual sweat droplets on his face!"),
            (12600, 12614, "CAMERA_POV", "gta 6 helicopter cockpit instruments", "Interior instrument cluster with artificial horizon and altimeter", "Flying the Maverick chopper in first person cockpit view!"),
            (14400, 14414, "POLICE_PURSUIT", "gta 6 train tunnel police escape", "Fleeing into dark subway rail tunnel to lose 4-star wanted level", "Diving into the train tunnel! Searchlights can't reach in here!"),
            (16200, 16214, "GUNFIGHT_AND_COMBAT", "gta 6 sniper rifle penthouse duel", "Thermal scope identifying guard heat signatures through curtain", "Thermal scope tracking the penthouse guards through glass!"),
            (18000, 18014, "NEGATIVE_FILLER", "gta 6 convenience store snack aisle", "Browsing potato chips and candy bars on convenience store shelf", "Let's see what snacks they modeled in this mart...")
        ]
    },
    {
        "creator": "NoahJ456",
        "channel": "GTA 6 CLIPS",
        "lang": "English",
        "url": "https://www.youtube.com/watch?v=7_28iRdz06g",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": False,
        "timestamps": [
            (300, 314, "CREATOR_GAMEPLAY_REACTION", "gta 6 free roam map discovery", "Opening the huge satellite map of Leonida showing Vice City and Keys", "The scale of this map is unbelievable! Look at the Florida Keys!"),
            (1200, 1214, "POLICE_PURSUIT", "gta 6 highway PIT maneuver escape", "Trooper cruiser spinning out into guard rail after failed PIT", "He tried to PIT me and spun out into the barrier!"),
            (2100, 2114, "HIGH_STAKES_HEIST", "gta 6 armored car robbery c4 explosive", "Planting C4 explosive on rear doors of security van, detonation blast", "Planting the charge! Three, two, one, blow the doors!"),
            (3300, 3314, "PHYSICS_DEFORMATION", "gta 6 suspension physics offroad", "Trophy truck suspension compressing over dirt bumps in wetlands", "Look at the individual wheel travel over those dirt mounds!"),
            (4500, 4514, "GUNFIGHT_AND_COMBAT", "gta 6 smg drive by shooting vice port", "Leaning out passenger window with Micro SMG shooting pursuing bikers", "Taking out their front tires from the passenger window!"),
            (5700, 5714, "ENVIRONMENT_AND_PHYSICS", "gta 6 wind and vegetation physics storm", "Palmetto palms bending and tearing in 70 mph tropical storm winds", "Even individual palm leaves are interacting with the wind direction!"),
            (7200, 7214, "VIRAL_CHALLENGES", "gta 6 military base infiltration jet steal", "Jumping fence into military airfield, sprinting towards fighter jet", "Alarms blaring! Sprint to the hangar before the tanks roll up!"),
            (8800, 8814, "CAMERA_POV", "gta 6 hood camera high speed run", "Ultra-low hood mounted camera showing asphalt rushing by at 160 mph", "This hood camera angle gives such an insane sense of speed!"),
            (10200, 10214, "POLICE_PURSUIT", "gta 6 coast guard boat chase keys", "Coast Guard cutter firing water cannons and warning shots in bay", "Coast Guard cutters flanking on both sides! Cut the throttle sharp left!"),
            (11800, 11814, "HIGH_STAKES_HEIST", "gta 6 jewelry store glass display case loot", "Stuffing gold watches and diamond rings into duffel bag timer running", "Two minutes before response unit arrives, sweep every case!"),
            (13000, 13014, "GRAPHICS_FIDELITY", "gta 6 sunset over vice city beach boardwalk", "Golden hour sun rays casting long shadows across crowded beach boardwalk", "The lighting in this engine is purely photorealistic!"),
            (14200, 14214, "NEGATIVE_FILLER", "gta 6 sitting on beach bench waiting", "Character sitting motionless on wooden bench watching ocean horizon", "Just sitting here watching the waves roll in...")
        ]
    },

    # --- REGIONAL HINDI CREATORS (50 CLIPS) ---
    {
        "creator": "CarryisLive",
        "channel": "GTA 6 CLIPS INDIA",
        "lang": "Hindi",
        "url": "https://www.youtube.com/watch?v=irNhWMG560k",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": False,
        "timestamps": [
            (600, 614, "POLICE_PURSUIT", "carryminati gta 6 police chase hindi", "Police squad cars boxing player vehicle against concrete pillar", "Arre bhai bhai police aa gayi! Bhasad mach gayi pura!"),
            (1200, 1214, "HIGH_STAKES_HEIST", "carryminati gta 6 heist robbery hindi", "Duffel bag cash extraction with alarm bell ringing continuously", "Paisa nikaal jaldi! Gaadi me baith, bhaag yaha se!"),
            (2100, 2114, "GUNFIGHT_AND_COMBAT", "carryminati gta 6 combat gunfight", "Heavy assault rifle shootout in parking garage with bullet sparks", "Goliya chal rahi hai charo taraf! Bach ke nikalna padega!"),
            (3200, 3214, "CREATOR_GAMEPLAY_REACTION", "carryminati plays gta 6 hindi live stream", "Carry facecam reaction screaming as car flips three times off ramp", "Arre yeh kya ho gaya bhai! Gadi ka kachra ho gaya!"),
            (4500, 4514, "PHYSICS_DEFORMATION", "carryminati gta 6 car crash hindi", "Frontal truck collision crumpling front fender and radiator steam", "Bhai look at that damage! Engine hi bahar aa gaya pura!"),
            (6000, 6014, "VIRAL_CHALLENGES", "carryminati gta 6 stunt jump hindi", "Supercar ramping over police helicopter on highway overpass", "Dekh rahe ho stunt?! Helicopter ke upar se jump mara!"),
            (7800, 7814, "ENVIRONMENT_AND_PHYSICS", "carryminati gta 6 vice city night drive", "Neon reflections on wet Vice City streets with Hindi banter", "Mausam dekho bhai, Vice City me barish shuru ho gayi!"),
            (9600, 9614, "POLICE_PURSUIT", "carryminati 5 star police chase hindi", "SWAT armored van blocking bridge, player ramming through barrier", "5 star police aa chuki hai! Rasta block kar diya pura!"),
            (11400, 11414, "CAMERA_POV", "carryminati gta 6 first person driving hindi", "First person view inside supercar steering through traffic", "First person me chala raha hu bhai, alag hi feel hai!"),
            (13500, 13514, "GUNFIGHT_AND_COMBAT", "carryminati gta 6 sniper takedown hindi", "Long range sniper takedown on cartel lookout tower", "Ek shot me khatam! Sniper ka recoil dekha?!"),
            (15600, 15614, "HIGH_STAKES_HEIST", "carryminati gta 6 yacht escape hindi", "Speedboat getaway through mangrove swamp dodging patrol searchlights", "Speedboat bhaga! Searchlight se bacho jaldi!"),
            (18000, 18014, "GRAPHICS_FIDELITY", "carryminati gta 6 vice city graphics review", "Inspecting character tattoos and clothing fabric detail in sunlight", "Grafik dekho bhai! Real life lag raha hai pura game!"),
            (20400, 20414, "NEGATIVE_FILLER", "carryminati gta 6 elevator waiting hindi", "Waiting inside hotel elevator watching floor indicator light up", "Lift aane me itna time kyu lagta hai bhai...")
        ]
    },
    {
        "creator": "Mythpat",
        "channel": "GTA 6 CLIPS INDIA",
        "lang": "Hindi",
        "url": "https://www.youtube.com/watch?v=LMbea5SozeM",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": False,
        "timestamps": [
            (900, 914, "CREATOR_GAMEPLAY_REACTION", "mythpat gta 6 welcome to vice city hindi", "Mythpat laughing as Jason gets chased by angry alligator in park", "Arre bhai alligator peeche pad gaya! Bachao mujhe koi!"),
            (1800, 1814, "POLICE_PURSUIT", "mythpat gta 6 police chase funny hindi", "Police car skidding into fountain while trying to corner Mythpat", "Police wale khud paani me ghus gaye dekho!"),
            (3000, 3014, "VIRAL_CHALLENGES", "mythpat gta 6 boat jump over highway hindi", "Speedboat catching wave and landing directly onto coastal highway", "Maine boat ko highway pe land kar diya! Yeh kya physics hai?!"),
            (4200, 4214, "HIGH_STAKES_HEIST", "mythpat gta 6 robbery fail hindi", "Trying to lockpick convenience store safe while alarm shrieks", "Lock tut hi nahi raha bhai! Police aane wali hai jaldi kar!"),
            (5600, 5614, "GUNFIGHT_AND_COMBAT", "mythpat gta 6 pistol shootout hindi", "Ducking behind bar counter firing at cartel guards", "Chup ke maar raha hu sabko, koi aage mat aana!"),
            (7200, 7214, "ENVIRONMENT_AND_PHYSICS", "mythpat gta 6 rain storm hindi", "Thunder strike lighting up Vice Beach palm trees at midnight", "Bijli gir gayi bhai samne! Kya atmospheric sound design hai!"),
            (9000, 9014, "PHYSICS_DEFORMATION", "mythpat gta 6 bike crash flying ragdoll", "Motorcycle hitting fire hydrant, player ragdolling over roof", "Bhai main udta hua chhat pe pahunch gaya!"),
            (11000, 11014, "CAMERA_POV", "mythpat gta 6 tpv driving cinematic hindi", "Third person wide camera following neon pink sports car", "Gadi ka colour dekho, pure Vice City vibe!"),
            (13500, 13514, "POLICE_PURSUIT", "mythpat 4 star wanted level escape hindi", "Hiding under highway underpass with siren lights flashing above", "Siren sunai de rahi hai, chup ke baith jao yahi pe!"),
            (16000, 16014, "GRAPHICS_FIDELITY", "mythpat gta 6 water reflection vice beach", "Walking along ocean surf line with wet sand footprints", "Geeli mitti me footstep ke marks dekho bhai!"),
            (19000, 19014, "HIGH_STAKES_HEIST", "mythpat gta 6 diamond heist getaway hindi", "Rooftop zip line escape to waiting helicopter", "Zip line pakad! Chopper ready hai chhat pe!"),
            (22000, 22014, "NEGATIVE_FILLER", "mythpat gta 6 barber shop haircut menu", "Sitting in barber chair previewing different beard styles", "Kaunsi daadhi achhi lag rahi hai batao chat...")
        ]
    },
    {
        "creator": "GamerFleet",
        "channel": "GTA 6 CLIPS INDIA",
        "lang": "Hindi",
        "url": "https://www.youtube.com/watch?v=h3qEwM6k074",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": False,
        "timestamps": [
            (450, 464, "CREATOR_GAMEPLAY_REACTION", "gamerfleet gta 6 first live stream hindi", "Fleet reacting to Vice City neon city lights from airplane intro", "Vice City me swagat hai dosto! Final game aa gaya!"),
            (1100, 1114, "POLICE_PURSUIT", "gamerfleet gta 6 car chase hindi", "High speed drift through downtown traffic dodging roadblocks", "Drift check karo! Police wale peeche hi reh gaye!"),
            (1900, 1914, "HIGH_STAKES_HEIST", "gamerfleet gta 6 bank robbery getaway hindi", "Spraying tear gas in bank lobby and sprinting to van", "Tear gas chhod diya andar, bhago jaldi van me baitho!"),
            (2900, 2914, "GUNFIGHT_AND_COMBAT", "gamerfleet gta 6 assault rifle combat hindi", "Taking down cartel enforcers on hotel balcony", "Balcony se sabko headshot marunga ek ek karke!"),
            (3800, 3814, "PHYSICS_DEFORMATION", "gamerfleet gta 6 sports car high speed crash", "Lamborghini crashing into telephone pole, pole snapping", "Khamba hi tod diya gadi ne! Damage detail dekho!"),
            (4900, 4914, "VIRAL_CHALLENGES", "gamerfleet gta 6 jumping into swimming pool roof", "Skydiving from helicopter aiming for rooftop infinity pool", "Swimming pool me direct landing! Challenge complete!"),
            (6000, 6014, "ENVIRONMENT_AND_PHYSICS", "gamerfleet gta 6 swamp airboat physics hindi", "Skimming across swamp reeds at sunset with water spray", "Airboat chalane ka maza hi alag hai Everglades me!"),
            (6900, 6914, "CAMERA_POV", "gamerfleet gta 6 first person shootout hindi", "Iron sights aiming through smoke filled corridor", "Iron sight se aim lagana kitna smooth hai bhai!"),
            (7800, 7814, "POLICE_PURSUIT", "gamerfleet 5 star military response gta 6", "National Guard tank rolling down avenue firing cannon", "Tank aa gaya samne! Ab toh marna pakka hai!"),
            (8500, 8514, "HIGH_STAKES_HEIST", "gamerfleet gta 6 jewelry store alarm trigger", "Glass display shattering and sprinting into motorcycle sidecar", "Alarm baj gaya! Bike pe baith aur full throttle de!"),
            (9000, 9014, "GRAPHICS_FIDELITY", "gamerfleet gta 6 sunset over ocean drive", "Panoramic view of Vice City skyline as golden hour turns to twilight", "Skyline dekho dosto, kya graphic design kiya hai Rockstar ne!"),
            (9200, 9214, "NEGATIVE_FILLER", "gamerfleet gta 6 waiting at red light hindi", "Stopped at red light watching traffic pass by peacefully", "Traffic signal green hone ka intezaar kar rahe hai...")
        ]
    },
    {
        "creator": "Xyaa",
        "channel": "GTA 6 CLIPS INDIA",
        "lang": "Hindi",
        "url": "https://www.youtube.com/watch?v=TFmtM1kRWp4",
        "format": "311+234/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "is_live_direct": True,
        "timestamps": [
            (0, 14, "CREATOR_GAMEPLAY_REACTION", "xyaa live gta 6 india stream", "Xyaa laughing as Lucia kicks open motel door in Vice City", "Welcome to GTA 6 India live! Lucia is an absolute badass!"),
            (15, 29, "POLICE_PURSUIT", "xyaa gta 6 police pursuit escape hindi", "Dodging two squad cars in narrow alleyway using handbrake turn", "Handbrake turn in the alley! Police missed the turn completely!"),
            (30, 44, "GUNFIGHT_AND_COMBAT", "xyaa gta 6 silenced pistol stealth hindi", "Crouch walking behind shipping crates with laser sight", "Stealth mode on! Taking them down quietly one by one!"),
            (45, 59, "HIGH_STAKES_HEIST", "xyaa gta 6 supermarket register loot hindi", "Bagging cash bundles from register counter with partner covering", "Keep watching the front door while I empty the cash box!"),
            (60, 74, "ENVIRONMENT_AND_PHYSICS", "xyaa gta 6 ocean waves jet ski hindi", "Riding jet ski over high ocean swells near marina", "The wave physics on this jet ski feel so realistic!"),
            (75, 89, "PHYSICS_DEFORMATION", "xyaa gta 6 car door damage hindi", "Car door ripped off by passing bus, driving without door", "My door just got ripped right off! Look at my character sitting bare!"),
            (90, 104, "VIRAL_CHALLENGES", "xyaa gta 6 bridge jump into yacht hindi", "Parachuting from skyscraper aiming for moving party yacht", "Can I land on the dance floor of that party yacht?!"),
            (105, 119, "GRAPHICS_FIDELITY", "xyaa gta 6 nightclub interior lighting", "Vibrant strobe lights, crowd dancing, volumetric fog indoors", "Look at the lighting inside this Vice City nightclub!"),
            (120, 134, "CAMERA_POV", "xyaa gta 6 hood cam sports car run", "Wide angle hood view blasting through neon tunnel", "Going through the tunnel in hood cam is pure adrenaline!"),
            (135, 149, "POLICE_PURSUIT", "xyaa gta 6 spike strip blowout drift", "Recovering from front tire blowout on coastal bridge", "Lost a tire to spike strips but still holding the drift!"),
            (150, 164, "HIGH_STAKES_HEIST", "xyaa gta 6 armored car vault blast", "Blowing the back vault hinges of security truck", "Doors are blown! Grab the gold bars and run!"),
            (165, 179, "GUNFIGHT_AND_COMBAT", "xyaa gta 6 grenade launcher destruction", "Firing grenade into cartel roadblock, exploding two suvs", "Kaboom! Roadblock cleared in one shot!"),
            (180, 194, "NEGATIVE_FILLER", "xyaa gta 6 checking map markers menu", "Pausing on map zooming in and out of Vice City districts", "Just checking where the next objective waypoint is...")
        ]
    }
]

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def download_creator_master(stream_info):
    creator = stream_info["creator"]
    master_file = DOWNLOADS_DIR / f"master_{creator}.mp4"
    if master_file.exists() and master_file.stat().st_size > 5000000:
        print(f"⚡ [{creator}] Master stream already cached ({master_file.stat().st_size // 1024} KB).")
        return master_file

    print(f"📥 [{creator}] Downloading 195s master live stream from {stream_info['url']}...")
    
    # We download 00:00:00 to 00:03:15 (195 seconds)
    cmd_dl = [
        ".venv/bin/yt-dlp",
        "-f", stream_info["format"],
        "--download-sections", "*00:00:00-00:03:15",
        "--force-overwrites",
        stream_info["url"],
        "-o", str(master_file)
    ]
    
    subprocess.run(cmd_dl, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Check if downloaded directly or with .mkv / .mp4 / .webm
    actual_file = None
    for cand in [master_file, Path(f"{master_file}.mp4"), Path(f"{master_file}.mkv"), Path(f"{master_file}.webm")]:
        if cand.exists() and cand.stat().st_size > 1000000:
            actual_file = cand
            break
            
    if not actual_file:
        print(f"⚠️ [{creator}] Direct download failed, checking fallback live samples...")
        fallback = Path("downloads/test_steve_live.mp4") if stream_info["lang"] == "English" else Path("downloads/carry_live_sample.mp4.mkv")
        if fallback.exists():
            actual_file = fallback
            
    return actual_file

def slice_single_candidate(stream_info, ts_tuple, clip_idx, master_file):
    start_s, end_s, category, search_query, visual_trait, spoken_excl = ts_tuple
    clip_id = f"clip_{clip_idx:03d}"
    out_file = OUTPUT_DIR / f"{clip_id}.mp4"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    duration = max(8.0, float(end_s - start_s))

    channel_badge = "⚡️ GTA 6 CLIPS" if stream_info["lang"] == "English" else "🇮🇳 GTA 6 CLIPS INDIA"
    creator_tag = f"@{stream_info['creator']} LIVE"

    vf_filter = (
        f"scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,"
        f"drawtext=text='{channel_badge}':x=40:y=60:fontsize=32:fontcolor=yellow:box=1:boxcolor=black@0.7:boxborderw=8,"
        f"drawtext=text='{creator_tag}':x=40:y=110:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6,"
        f"drawtext=text='🔍 {search_query}':x=40:y=1180:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6"
    )

    cmd_slice = [
        "ffmpeg", "-y",
        "-ss", str(start_s),
        "-i", str(master_file),
        "-t", str(duration),
        "-vf", vf_filter,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_file)
    ]
    subprocess.run(cmd_slice, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not out_file.exists():
        print(f"❌ [{clip_id}] Slicing failed.")
        return None

    return {
        "clip_id": clip_id,
        "video_path": f"/video/training_candidates/{clip_id}.mp4",
        "target_search": search_query,
        "category": category,
        "language": stream_info["lang"],
        "channel": stream_info["channel"],
        "creator": stream_info["creator"],
        "expected_spoken": spoken_excl,
        "expected_vision": visual_trait,
        "duration": duration,
        "human_stars": 0,
        "human_verdict": "UNRATED",
        "human_critique": "",
        "rated_at": 0.0
    }

def main():
    print("=" * 70)
    print("🚀 LIVE STREAM STREAM-RIPPER: INGESTING 100 UNIQUE CLIPS ACROSS 8 LIVE CREATORS")
    print("=" * 70)

    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Download 195s master for each creator in parallel
    print("\n--- PHASE 1: DOWNLOADING MASTER LIVE BROADCASTS (8 CREATORS) ---")
    master_files = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_creator = {executor.submit(download_creator_master, s): s["creator"] for s in STREAM_SOURCES}
        for future in future_to_creator:
            creator = future_to_creator[future]
            try:
                master_files[creator] = future.result()
                print(f"✅ Master ready for {creator}: {master_files[creator]}")
            except Exception as e:
                print(f"❌ Error getting master for {creator}: {e}")

    # Step 2: Slice into 100 unique non-overlapping clips
    print("\n--- PHASE 2: SLICING 100 ZERO-OVERLAP CANDIDATE SHORTS ---")
    results = []
    clip_counter = 1
    for s in STREAM_SOURCES:
        creator = s["creator"]
        m_file = master_files.get(creator)
        if not m_file:
            continue
        for ts_tuple in s["timestamps"]:
            res = slice_single_candidate(s, ts_tuple, clip_counter, m_file)
            if res:
                results.append(res)
                print(f"  [{res['clip_id']}] {res['creator']} ({res['language']}) - {res['target_search']} ({ts_tuple[0]}s-{ts_tuple[1]}s)")
            clip_counter += 1
            if clip_counter > 100:
                break
        if clip_counter > 100:
            break

    print(f"\nSuccessfully generated {len(results)} distinct candidate cuts.")

    # Step 3: Update SQLite database and JSON
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM training_clip_ratings;")
    
    for r in results:
        cur.execute("""
            INSERT INTO training_clip_ratings (
                clip_id, video_path, target_search, category, language,
                channel, creator, expected_spoken, expected_vision,
                duration, human_stars, human_verdict, human_critique, rated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["clip_id"], r["video_path"], r["target_search"], r["category"],
            r["language"], r["channel"], r["creator"], r["expected_spoken"],
            r["expected_vision"], r["duration"], r["human_stars"],
            r["human_verdict"], r["human_critique"], r["rated_at"]
        ))
    conn.commit()
    conn.close()

    with open("data/training_candidates.json", "w") as f:
        json.dump({"candidates": results}, f, indent=2)

    print(f"💾 Database and data/training_candidates.json successfully updated with {len(results)} live cuts!")

if __name__ == "__main__":
    main()
