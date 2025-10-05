# File: app.py
"""
PA Titans System Generator (Streamlit)
- Generates .pas system files (Planetary Annihilation: Titans)
- Ensures each .pas contains a JSON array [system] (PA expects an array)
- Distributes resource planets using polar coordinates and assigns
  perpendicular velocities for more stable orbits.
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

def perp_velocity(px: float, py: float, speed_scale: float = 1.0) -> (int, int):
    """
    Compute a velocity vector approximately perpendicular to the position vector.
    This gives planets a tangential velocity which results in orbital-like motion.
    speed_scale adjusts overall speed magnitude.
    """
    # Perpendicular to (px, py) is (-py, px) or (py, -px)
    # Normalize and scale
    mag = math.hypot(px, py)
    if mag == 0:
        return int(random.uniform(-50, 50)), int(random.uniform(-50, 50))
    vx = -py / mag
    vy = px / mag
    # Scale velocity with inverse sqrt(distance) for variety but controlled magnitude
    speed = speed_scale * (20000.0 / (math.sqrt(mag) + 1.0))
    return int(vx * speed), int(vy * speed)

# ----------------------
# System generation
# ----------------------
def generate_system(
    num_additional_planets: int = 3,
    starting_planet_radius: int = 400,
    starting_planet_metal: int = 100,
    additional_planet_radius: int = 300,
    base_metal_value: int = 50,
    system_name: str | None = None,
    rng_seed: int | None = None
) -> Dict:
    """
    Generate a PA Titans system as a Python dict.
    """

    if rng_seed is not None:
        random.seed(rng_seed)

    if system_name is None:
        system_name = f"Random System {num_additional_planets}+2"

    system = {
        "name": system_name,
        "description": f"Procedural system with 2 starting planets and {num_additional_planets} additional",
        "version": "1.0",
        "planets": []
    }

    # Create 2 starting planets (symmetrically positioned)
    starting_distance = 25000
    for i in range(2):
        px = starting_distance * (1 if i == 0 else -1)
        py = 0
        # small orbit-like velocity for starting planets
        vx, vy = perp_velocity(px, py, speed_scale=1.0)
        # Slight sign flip so each faces opposite direction
        if i == 1:
            vx, vy = -vx, -vy

        planet = {
            "name": f"Starting Planet {i+1}",
            "mass": 10000,
            "position_x": int(px),
            "position_y": int(py),
            "velocity_x": int(vx),
            "velocity_y": int(vy),
            "required_thrust_to_move": 0,
            "starting_planet": True,
            "respawn": False,
            "start_destroyed": False,
            "min_spawn_delay": 0,
            "max_spawn_delay": 0,
            "planet": {
                "seed": random.randint(0, 100000),
                "radius": starting_planet_radius,
                "heightRange": 50,
                "waterHeight": 0,
                "waterDepth": 0,
                "temperature": 50,
                "metalDensity": starting_planet_metal,
                "metalClusters": 50,
                "biomeScale": 50,
                "biome": random.choice(["earth", "desert", "lava", "moon", "tropical", "ice", "metal"])
            }
        }
        system["planets"].append(planet)

    # Create additional resource planets distributed around center
    for i in range(num_additional_planets):
        # Metal deviation ±10%
        metal_deviation = random.uniform(-0.1, 0.1)
        metal_amount = int(round(base_metal_value * (1 + metal_deviation)))

        # Angle and radial distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.randint(35000, 50000)

        px = distance * math.cos(angle)
        py = distance * math.sin(angle)

        # Perpendicular velocity for orbit-like motion
        vx, vy = perp_velocity(px, py, speed_scale=random.uniform(0.8, 1.2))

        planet = {
            "name": f"Resource Planet {i+1}",
            "mass": 5000,
            "position_x": int(px),
            "position_y": int(py),
            "velocity_x": int(vx),
            "velocity_y": int(vy),
            "required_thrust_to_move": 0,
            "starting_planet": False,
            "respawn": False,
            "start_destroyed": False,
            "min_spawn_delay": 0,
            "max_spawn_delay": 0,
            "planet": {
                "seed": random.randint(0, 100000),
                "radius": additional_planet_radius,
                "heightRange": 50,
                "waterHeight": 0,
                "waterDepth": 0,
                "temperature": random.randint(0, 100),
                "metalDensity": metal_amount,
                "metalClusters": 40,
                "biomeScale": 50,
                "biome": random.choice(["earth", "desert", "lava", "moon", "tropical", "ice", "metal"])
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
st.markdown("Generate balanced star systems for PA Titans. Files are saved as `.pas` (each contains a JSON array `[system]` required by PA).")

# Sidebar config
st.sidebar.header("System Configuration")

num_systems = st.sidebar.number_input("Number of Systems to Generate", min_value=1, max_value=50, value=5)
num_additional = st.sidebar.selectbox("Additional Planets", options=[1, 3, 5], index=1)
starting_radius = st.sidebar.slider("Starting Planet Radius", min_value=200, max_value=800, value=400, step=50)
starting_metal = st.sidebar.slider("Starting Planet Metal Density", min_value=50, max_value=150, value=100, step=10)
additional_radius = st.sidebar.slider("Additional Planet Radius", min_value=150, max_value=600, value=300, step=50)
base_metal = st.sidebar.slider("Base Metal Density (±10%)", min_value=20, max_value=100, value=50, step=5)

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
    st.markdown(f"- Starting Planets: 2 (Radius: **{starting_radius}**, Metal: **{starting_metal}**)\n"
                f"- Additional Planets: **{num_additional}** (Radius: **{additional_radius}**, Metal base: **{base_metal}**) \n"
                f"- Total Systems: **{num_systems}**\n"
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
                system_name=system_name,
                rng_seed=rng
            )
            systems.append(system)

        st.session_state.generated_systems = systems
        st.success(f"✅ Generated {len(systems)} systems")

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
        with c2:
            st.markdown("**Planet Details**")
            for p in system['planets']:
                with st.expander(p['name']):
                    st.write(f"Radius: {p['planet']['radius']}")
                    st.write(f"Metal Density: {p['planet']['metalDensity']}")
                    st.write(f"Biome: {p['planet']['biome']}")
                    st.write(f"Starting Planet: {p.get('starting_planet', False)}")
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
            json_str = json.dumps(sys_obj, indent=2)  # no array wrapper
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
