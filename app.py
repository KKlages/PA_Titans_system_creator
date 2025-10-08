# File: app.py
"""
PA Titans System Generator (Streamlit) - Enhanced
- Generates .pas system files (Planetary Annihilation: Titans)
- Ensures each .pas contains a JSON array [system] (PA expects an array)
- Non-overlapping orbits with fixed distance intervals
- Perpendicular velocities for stable circular orbits
"""
import streamlit as st
import json
import random
import io
import zipfile
import math
from datetime import datetime
from typing import List, Dict

st.set_page_config(page_title="PA Titans System Generator", page_icon="🌍", layout="wide")

# ----------------------
# Utility functions
# ----------------------
def sanitize_filename(name: str) -> str:
    """Make a safe filename from a system name."""
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in name).replace(" ", "_")

def calculate_orbital_velocity(distance: float, mass: float = 10000) -> float:
    """
    Calculate orbital velocity for circular orbit.
    Uses simplified physics: v = sqrt(GM/r), scaled for PA.
    """
    if distance == 0:
        return 0
    # Scale factor tuned for PA Titans orbital mechanics
    return 15000 / math.sqrt(distance)

def perp_velocity(px: float, py: float, distance: float) -> tuple[int, int]:
    """
    Compute perpendicular velocity vector for circular orbit.
    Returns velocity components that are tangent to the orbit.
    """
    if distance == 0:
        return 0, 0
    
    # Calculate orbital speed based on distance
    speed = calculate_orbital_velocity(distance)
    
    # Perpendicular direction (tangent to orbit)
    # For position (px, py), perpendicular is (-py, px) normalized
    magnitude = math.sqrt(px * px + py * py)
    if magnitude == 0:
        return 0, 0
    
    # Normalize and scale by orbital speed
    vx = (-py / magnitude) * speed
    vy = (px / magnitude) * speed
    
    return int(round(vx)), int(round(vy))

# ----------------------
# System generation
# ----------------------
def generate_system(
    num_additional_planets: int = 3,
    starting_planet_radius: int = 400,
    starting_planet_metal: int = 100,
    additional_planet_radius: int = 300,
    base_metal_value: int = 50,
    base_orbital_distance: int = 25000,
    orbital_distance_step: int = 10000,
    system_name: str | None = None,
    rng_seed: int | None = None
) -> Dict:
    """
    Generate a PA Titans system as a Python dict with non-overlapping orbits.
    """

    if rng_seed is not None:
        random.seed(rng_seed)

    if system_name is None:
        system_name = f"Random System {num_additional_planets}+2"

    system = {
        "name": system_name,
        "description": f"Procedural system with 2 starting planets and {num_additional_planets} additional",
        "version": "1.0",
        "creator": "PA Titans System Generator",
        "players": [2, 10],
        "planets": []
    }

    total_planets = 2 + num_additional_planets
    
    # Calculate fixed orbital distances for all planets (no overlaps)
    orbital_distances = [base_orbital_distance + i * orbital_distance_step for i in range(total_planets)]
    
    # Generate random but distinct orbital angles for each planet
    orbital_angles = random.sample(range(0, 360, 10), total_planets)  # Sample every 10 degrees

    # Create 2 starting planets at first two orbital shells
    for i in range(2):
        distance = orbital_distances[i]
        angle = orbital_angles[i]
        angle_rad = math.radians(angle)
        
        px = distance * math.cos(angle_rad)
        py = distance * math.sin(angle_rad)
        
        # Calculate perpendicular velocity for stable orbit
        vx, vy = perp_velocity(px, py, distance)

        planet = {
            "name": f"Starting Planet {i+1}",
            "mass": 10000,
            "position_x": round(px, 2),
            "position_y": round(py, 2),
            "velocity_x": vx,
            "velocity_y": vy,
            "required_thrust_to_move": 0,
            "starting_planet": True,
            "respawn": False,
            "start_destroyed": False,
            "min_spawn_delay": 0,
            "max_spawn_delay": 0,
            "planet": {
                "seed": random.randint(0, 999999),
                "radius": starting_planet_radius,
                "heightRange": 50,
                "waterHeight": 0,
                "waterDepth": 50,
                "temperature": 50,
                "metalDensity": starting_planet_metal,
                "metalClusters": 50,
                "biomeScale": 50,
                "biome": random.choice(["earth", "desert", "lava", "moon", "tropical", "ice", "metal"]),
                "symmetryType": "terrain and CSG",
                "symmetricalMetal": True,
                "symmetricalStarts": True,
                "numArmies": 2,
                "landingZonesPerArmy": 0,
                "landingZoneSize": 0
            },
            "orbit": {
                "distance": distance,
                "period": round(distance / 1000, 1)
            }
        }
        system["planets"].append(planet)

    # Create additional resource planets at remaining orbital shells
    for i in range(num_additional_planets):
        distance = orbital_distances[i + 2]
        angle = orbital_angles[i + 2]
        angle_rad = math.radians(angle)
        
        # Metal deviation ±10%
        metal_deviation = random.uniform(-0.1, 0.1)
        metal_amount = int(round(base_metal_value * (1 + metal_deviation)))

        px = distance * math.cos(angle_rad)
        py = distance * math.sin(angle_rad)

        # Perpendicular velocity for stable circular orbit
        vx, vy = perp_velocity(px, py, distance)

        # Determine planet type based on distance
        planet_type = "Moon" if distance < base_orbital_distance * 2 else "Planet"

        planet = {
            "name": f"Resource {planet_type} {i+1}",
            "mass": 10000,
            "position_x": round(px, 2),
            "position_y": round(py, 2),
            "velocity_x": vx,
            "velocity_y": vy,
            "required_thrust_to_move": 5,
            "starting_planet": False,
            "respawn": False,
            "start_destroyed": False,
            "min_spawn_delay": 0,
            "max_spawn_delay": 0,
            "planet": {
                "seed": random.randint(0, 999999),
                "radius": additional_planet_radius,
                "heightRange": 35,
                "waterHeight": 0,
                "waterDepth": 50,
                "temperature": random.randint(0, 100),
                "metalDensity": metal_amount,
                "metalClusters": 40,
                "biomeScale": 50,
                "biome": random.choice(["earth", "desert", "lava", "moon", "tropical", "ice", "metal", "gas"])
            },
            "orbit": {
                "distance": distance,
                "period": round(distance / 1000, 1)
            }
        }
        system["planets"].append(planet)

    return system

# ----------------------
# ZIP / file helpers
# ----------------------
def create_zip_file(systems: List[Dict]) -> io.BytesIO:
    """
    Create a zip archive that contains systems as .pas files inside pa/maps/.
    Each .pas contains a JSON array [system] as required by PA.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, system in enumerate(systems):
            safe_name = sanitize_filename(system.get("name", f"system_{i+1}"))
            filename = f"{safe_name}_{i+1}.pas"
            # PA expects the system as an array in the file
            json_str = json.dumps([system], indent=2)
            zf.writestr(f"pa/maps/{filename}", json_str)

        # Add a minimal modinfo.json for server_mod usage
        modinfo = {
            "context": "server",
            "identifier": "generated_maps",
            "display_name": "Generated Maps",
            "description": "Custom systems generated by Streamlit tool",
            "author": "PA Titans Community",
            "version": "1.0",
            "priority": 100
        }
        zf.writestr("modinfo.json", json.dumps(modinfo, indent=2))

        # README
        readme = (
            "# PA Titans Generated Systems\n\n"
            "Copy the 'generated_maps' folder into your Planetary Annihilation server_mods directory.\n\n"
            "Windows: %LOCALAPPDATA%\\Uber Entertainment\\Planetary Annihilation\\server_mods\\\n"
            "Linux: ~/.local/Uber Entertainment/Planetary Annihilation/server_mods/\n"
            "Mac: ~/Library/Application Support/Uber Entertainment/Planetary Annihilation/server_mods/\n\n"
            "Structure inside the zip:\n\n"
            "generated_maps/\n"
            "  ├─ modinfo.json\n"
            "  └─ pa/\n"
            "     └─ maps/\n"
            "        ├─ <system>.pas\n"
        )
        zf.writestr("README.txt", readme)

    zip_buffer.seek(0)
    return zip_buffer

# ----------------------
# Streamlit UI
# ----------------------
st.title("🌍 Planetary Annihilation: Titans System Generator")
st.markdown("Generate balanced star systems with **non-overlapping orbits** for PA Titans. Files are saved as `.pas` (each contains a JSON array `[system]` required by PA).")

# Sidebar config
st.sidebar.header("System Configuration")

num_systems = st.sidebar.number_input("Number of Systems to Generate", min_value=1, max_value=50, value=5)
num_additional = st.sidebar.selectbox("Additional Planets", options=[1, 3, 5, 7, 10], index=1)

st.sidebar.subheader("Planet Properties")
starting_radius = st.sidebar.slider("Starting Planet Radius", min_value=200, max_value=800, value=400, step=50)
starting_metal = st.sidebar.slider("Starting Planet Metal Density", min_value=50, max_value=150, value=100, step=10)
additional_radius = st.sidebar.slider("Additional Planet Radius", min_value=150, max_value=600, value=300, step=50)
base_metal = st.sidebar.slider("Base Metal Density (±10%)", min_value=20, max_value=100, value=50, step=5)

st.sidebar.subheader("Orbital Configuration")
base_distance = st.sidebar.number_input("Base Orbital Distance", min_value=10000, max_value=50000, value=25000, step=5000,
                                        help="Distance of first orbital shell from center")
distance_step = st.sidebar.number_input("Orbital Distance Step", min_value=5000, max_value=20000, value=10000, step=1000,
                                        help="Distance between each orbital shell")

use_custom_name = st.sidebar.checkbox("Use Custom System Name")
custom_name_base = ""
if use_custom_name:
    custom_name_base = st.sidebar.text_input("System Name Base", value="Custom System")

# Reproducibility
st.sidebar.markdown("---")
st.sidebar.subheader("Randomness / Seed")
use_seed = st.sidebar.checkbox("Use fixed RNG seed (reproducible)")
seed_val = None
if use_seed:
    seed_val = st.sidebar.number_input("Seed value", min_value=0, max_value=2**31-1, value=random.randint(0, 2**31-1))

# Preview + Actions
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Configuration Summary")
    total_planets_per_system = 2 + num_additional
    max_distance = base_distance + (total_planets_per_system - 1) * distance_step
    st.markdown(f"- Starting Planets: **2** (Radius: **{starting_radius}**, Metal: **{starting_metal}**)\n"
                f"- Additional Planets: **{num_additional}** (Radius: **{additional_radius}**, Metal base: **{base_metal}**) \n"
                f"- Total Planets per System: **{total_planets_per_system}**\n"
                f"- Total Systems: **{num_systems}**\n"
                f"- Orbital Range: **{base_distance:,}** to **{max_distance:,}** units\n"
                f"- Orbital Spacing: **{distance_step:,}** units\n"
                f"- Reproducible Seed: **{seed_val if use_seed else 'No'}**")

with col2:
    if st.button("🎲 Generate Systems", type="primary"):
        systems = []
        for i in range(num_systems):
            system_name = None
            if use_custom_name and custom_name_base:
                system_name = f"{custom_name_base} {i+1}"
            # If reproducible, vary seed per system deterministically
            rng = None
            if use_seed:
                rng = int(seed_val + i)
            system = generate_system(
                num_additional_planets=num_additional,
                starting_planet_radius=starting_radius,
                starting_planet_metal=starting_metal,
                additional_planet_radius=additional_radius,
                base_metal_value=base_metal,
                base_orbital_distance=base_distance,
                orbital_distance_step=distance_step,
                system_name=system_name,
                rng_seed=rng
            )
            systems.append(system)

        st.session_state.generated_systems = systems
        st.success(f"✅ Generated {len(systems)} systems with non-overlapping orbits")

# Display and downloads
if 'generated_systems' in st.session_state:
    st.markdown("---")
    st.subheader("Generated Systems")

    tab1, tab2 = st.tabs(["📋 Preview", "⬇️ Download"])
    with tab1:
        idx = st.selectbox("Select system to preview", options=range(len(st.session_state.generated_systems)),
                           format_func=lambda x: st.session_state.generated_systems[x]['name'])
        system = st.session_state.generated_systems[idx]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**System Information**")
            st.json({"name": system['name'], "description": system['description'], "total_planets": len(system['planets'])})
            
            st.markdown("**Orbital Structure**")
            for p in system['planets']:
                orbit_info = p.get('orbit', {})
                st.write(f"• {p['name']}: {orbit_info.get('distance', 'N/A'):,} units")
                
        with c2:
            st.markdown("**Planet Details**")
            for p in system['planets']:
                with st.expander(p['name']):
                    orbit_info = p.get('orbit', {})
                    st.write(f"**Orbital Distance:** {orbit_info.get('distance', 'N/A'):,} units")
                    st.write(f"**Orbital Period:** {orbit_info.get('period', 'N/A')} (relative)")
                    st.write(f"**Radius:** {p['planet']['radius']}")
                    st.write(f"**Metal Density:** {p['planet']['metalDensity']}")
                    st.write(f"**Biome:** {p['planet']['biome'].title()}")
                    st.write(f"**Starting Planet:** {p.get('starting_planet', False)}")
                    st.write(f"**Position:** ({p['position_x']:.0f}, {p['position_y']:.0f})")
                    st.write(f"**Velocity:** ({p['velocity_x']}, {p['velocity_y']})")
        
        with st.expander("View full JSON"):
            st.json(system)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            zip_buffer = create_zip_file(st.session_state.generated_systems)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📦 Download All Systems (ZIP)",
                data=zip_buffer,
                file_name=f"pa_titans_systems_{timestamp}.zip",
                mime="application/zip",
                use_container_width=True
            )
        with c2:
            sel = st.selectbox("Download individual system", options=range(len(st.session_state.generated_systems)),
                               format_func=lambda x: st.session_state.generated_systems[x]['name'],
                               key="download_select")
            sys_obj = st.session_state.generated_systems[sel]
            json_str = json.dumps([sys_obj], indent=2)  # Wrap in array for PA
            filename = f"{sanitize_filename(sys_obj['name'])}.pas"
            st.download_button(
                label=f"⬇️ Download {sys_obj['name']}",
                data=json_str,
                file_name=filename,
                mime="application/json",
                use_container_width=True
            )


# Footer / Installation note
st.markdown("---")
st.markdown(
    "### 📖 Installation Instructions\n\n"
    "1. Download the ZIP and copy the extracted `generated_maps` folder into:\n"
    "- Windows: `%LOCALAPPDATA%\\Uber Entertainment\\Planetary Annihilation\\server_mods\\`\n"
    "- Linux: `~/.local/Uber Entertainment/Planetary Annihilation/server_mods/`\n"
    "- Mac: `~/Library/Application Support/Uber Entertainment/Planetary Annihilation/server_mods/`\n\n"
    "2. Launch PA Titans → Community Mods → Enable 'Generated Maps'.\n\n"
    "Alternatively, for local single-system use you can copy a single `.pas` into your local systems folder\n"
    "`ui/main_game/live_game/systems/` (game installs differ by platform).\n"
)

st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ for the PA Titans community")