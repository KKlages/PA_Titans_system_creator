# File: app.py
"""
PA Titans System Generator (Streamlit)
- Uses PlanetarySystemGenerator to produce stable .pas files (each file contains a JSON array: [system])
- Adds required metadata fields (creator, players) and planet placeholders (planetCSG, landing_zones)
- Distributes resource planets with angular spacing and perpendicular velocities for stable motion
"""
import streamlit as st
import json
import random
import io
import zipfile
import math
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple

st.set_page_config(page_title="PA Titans System Generator", page_icon="🌍", layout="wide")


# ----------------------
# Utilities
# ----------------------
def sanitize_filename(name: str) -> str:
    """Make a safe filename from a system name."""
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in name).strip().replace(" ", "_")


# ----------------------
# Generator (adapted from your reference)
# ----------------------
class PlanetarySystemGenerator:
    """Generator for Planetary Annihilation: Titans system maps"""

    BIOMES = ["earth", "tropical", "moon", "lava", "desert", "ice"]

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_system(
        self,
        num_starting_planets: int = 2,
        num_resource_planets: int = 5,
        system_name: str = "Random System",
        system_radius: int = 50000,
        orbital_velocity_range: Tuple[float, float] = (50.0, 150.0),
        creator: str = "AutoGenerator",
        players: Tuple[int, int] = (2, 10),
    ) -> Dict:
        """Generate a complete planetary system dict suitable for saving as .pas (wrapped later as [system])"""
        system = {
            "name": f"{system_name} {num_starting_planets}+{num_resource_planets}",
            "description": f"Procedural system with {num_starting_planets} starting planets and {num_resource_planets} additional",
            "creator": creator,
            "version": "1.0",
            "players": list(players),
            "planets": []
        }

        # Starting planets (evenly spaced around circle, symmetric)
        starting_positions = self._generate_starting_positions(num_starting_planets, system_radius * 0.4)
        for i, pos in enumerate(starting_positions):
            planet = self._create_starting_planet(f"Starting Planet {i+1}", position=pos, orbital_velocity_range=orbital_velocity_range)
            system["planets"].append(planet)

        # Resource planets (spaced angles, avoid overlap)
        used_angles: Set[float] = set()
        for i in range(num_resource_planets):
            planet = self._create_resource_planet(
                f"Resource Planet {i+1}",
                system_radius=system_radius,
                orbital_velocity_range=orbital_velocity_range,
                used_angles=used_angles
            )
            system["planets"].append(planet)

        return system

    def _generate_starting_positions(self, count: int, radius: float) -> List[Tuple[float, float]]:
        positions = []
        if count <= 0:
            return positions
        angle_step = 2 * math.pi / count
        for i in range(count):
            angle = i * angle_step
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            positions.append((x, y))
        return positions

    def _create_starting_planet(self, name: str, position: Tuple[float, float], orbital_velocity_range: Tuple[float, float]) -> Dict:
        x, y = position
        distance = math.hypot(x, y)
        if distance > 0:
            velocity_magnitude = random.uniform(*orbital_velocity_range)
            # perpendicular vector: (-y, x)
            velocity_x = -y / distance * velocity_magnitude
            velocity_y = x / distance * velocity_magnitude
        else:
            velocity_x, velocity_y = 0.0, random.uniform(*orbital_velocity_range)

        return {
            "name": name,
            "mass": 10000,
            "position_x": round(x, 2),
            "position_y": round(y, 2),
            "velocity_x": round(velocity_x, 2),
            "velocity_y": round(velocity_y, 2),
            "required_thrust_to_move": 0,
            "starting_planet": True,
            "respawn": False,
            "start_destroyed": False,
            "min_spawn_delay": 0,
            "max_spawn_delay": 0,
            "planet": {
                "seed": random.randint(1, 99999),
                "radius": 400,
                "heightRange": 50,
                "waterHeight": 0,
                "waterDepth": 0,
                "temperature": 50,
                "metalDensity": 100,
                "metalClusters": 50,
                "biomeScale": 50,
                "biome": "earth",
                "planetCSG": [],
                "landing_zones": {"list": [], "rules": []}
            }
        }

    def _create_resource_planet(self, name: str, system_radius: int, orbital_velocity_range: Tuple[float, float], used_angles: Set[float]) -> Dict:
        # choose angle not too close to existing ones (min angular separation = 30 degrees)
        min_sep = math.radians(30)
        attempts = 0
        while True:
            angle = random.uniform(0, 2 * math.pi)
            if not used_angles or all(abs((angle - a + math.pi) % (2 * math.pi) - math.pi) > min_sep for a in used_angles):
                used_angles.add(angle)
                break
            attempts += 1
            if attempts > 100:
                # fallback: accept whatever angle
                used_angles.add(angle)
                break

        distance = random.uniform(system_radius * 0.5, system_radius)
        x = distance * math.cos(angle)
        y = distance * math.sin(angle)

        # perpendicular velocity for orbit-like motion
        if distance > 0:
            velocity_magnitude = random.uniform(*orbital_velocity_range)
            velocity_x = -y / distance * velocity_magnitude
            velocity_y = x / distance * velocity_magnitude
        else:
            velocity_x, velocity_y = 0.0, random.uniform(*orbital_velocity_range)

        biome = random.choice(self.BIOMES)
        temperature = self._get_biome_temperature(biome)

        return {
            "name": name,
            "mass": 5000,
            "position_x": round(x, 2),
            "position_y": round(y, 2),
            "velocity_x": round(velocity_x, 2),
            "velocity_y": round(velocity_y, 2),
            "required_thrust_to_move": 0,
            "starting_planet": False,
            "respawn": False,
            "start_destroyed": False,
            "min_spawn_delay": 0,
            "max_spawn_delay": 0,
            "planet": {
                "seed": random.randint(1, 99999),
                "radius": 300,
                "heightRange": 50,
                "waterHeight": 0,
                "waterDepth": 0,
                "temperature": temperature + random.randint(-10, 10),
                "metalDensity": random.randint(45, 55),
                "metalClusters": 40,
                "biomeScale": 50,
                "biome": biome,
                "planetCSG": [],
                "landing_zones": {"list": [], "rules": []}
            }
        }

    def _get_biome_temperature(self, biome: str) -> int:
        temps = {
            "earth": 50,
            "tropical": 80,
            "moon": 70,
            "lava": 90,
            "desert": 85,
            "ice": 10
        }
        return temps.get(biome, 50)


# ----------------------
# ZIP / file helpers
# ----------------------
def create_zip_file(systems: List[Dict]) -> io.BytesIO:
    """
    Create a zip archive that contains systems as .pas files inside generated_maps/pa/maps/.
    Each file contains a JSON array [system] as required by PA.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, system in enumerate(systems):
            safe_name = sanitize_filename(system.get("name", f"system_{i+1}"))
            filename = f"{safe_name}_{i+1}.pas"
            json_str = json.dumps(system, indent=2) 
            # write into generated_maps/pa/maps/
            zf.writestr(f"generated_maps/pa/maps/{filename}", json_str)

        # Add a minimal modinfo.json for server_mod usage inside generated_maps/
        modinfo = {
            "context": "server",
            "identifier": "generated_maps",
            "display_name": "Generated Maps",
            "description": "Custom systems generated by Streamlit tool",
            "author": "PA Titans Community",
            "version": "1.0",
            "priority": 100
        }
        zf.writestr("generated_maps/modinfo.json", json.dumps(modinfo, indent=2))

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
        zf.writestr("generated_maps/README.txt", readme)

    zip_buffer.seek(0)
    return zip_buffer


# ----------------------
# Streamlit UI
# ----------------------
st.title("🌍 Planetary Annihilation: Titans System Generator")
st.markdown("Generate stable, PA-compatible `.pas` system files. Each .pas contains a JSON array `[system]` required by PA.")

# Sidebar config
st.sidebar.header("System Configuration")

num_systems = st.sidebar.number_input("Number of Systems to Generate", min_value=1, max_value=50, value=5)
num_additional = st.sidebar.selectbox("Additional (resource) planets", options=[1, 3, 5, 8], index=1)
starting_radius = st.sidebar.slider("Starting Planet Radius", min_value=200, max_value=800, value=400, step=50)
starting_metal = st.sidebar.slider("Starting Planet Metal Density", min_value=50, max_value=150, value=100, step=10)
additional_radius = st.sidebar.slider("Additional Planet Radius", min_value=150, max_value=600, value=300, step=50)
base_metal = st.sidebar.slider("Base Metal Density (resource planets)", min_value=20, max_value=100, value=50, step=5)
system_radius = st.sidebar.slider("System Radius (distance limit)", min_value=20000, max_value=100000, value=50000, step=5000)

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
    seed_val = st.sidebar.number_input("Seed value", min_value=0, max_value=2**31 - 1, value=random.randint(0, 2**31 - 1))

# Preview + Actions
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Configuration Summary")
    st.markdown(
        f"- Starting Planets: 2 (Radius: **{starting_radius}**, Metal: **{starting_metal}**)\n"
        f"- Additional Planets: **{num_additional}** (Radius: **{additional_radius}**, Metal base: **{base_metal}**) \n"
        f"- System radius limit: **{system_radius}**\n"
        f"- Total Systems to generate: **{num_systems}**\n"
        f"- Reproducible Seed: **{seed_val if use_seed else 'No'}**"
    )

with col2:
    if st.button("🎲 Generate Systems", type="primary"):
        generator = PlanetarySystemGenerator(seed=(seed_val if use_seed else None))
        systems = []
        for i in range(num_systems):
            # per-system deterministic seed if reproducible was requested
            rng = None
            if use_seed:
                rng = int((seed_val or 0) + i)
                generator = PlanetarySystemGenerator(seed=rng)
            system_name = None
            if use_custom_name and custom_name_base:
                system_name = f"{custom_name_base} {i+1}"
            else:
                system_name = f"Random System"

            system = generator.generate_system(
                num_starting_planets=2,
                num_resource_planets=num_additional,
                system_name=system_name,
                system_radius=system_radius,
                orbital_velocity_range=(50.0, 150.0),
                creator="Streamlit Generator",
                players=(2, 10)
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
        idx = st.selectbox("Select system to preview", options=list(range(len(st.session_state.generated_systems))),
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
            sel = st.selectbox("Download individual system", options=list(range(len(st.session_state.generated_systems))),
                               format_func=lambda x: st.session_state.generated_systems[x]['name'],
                               key="download_select")
            sys_obj = st.session_state.generated_systems[sel]
            # Wrap as an array (PA expects [system]) and provide .pas extension
            json_str = json.dumps([sys_obj], indent=2)
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
