#!/usr/bin/env python3
import os
import sys
import json
import zipfile
import pathlib
import ctypes
import re
from typing import Dict, List, Optional

try:
    import zstandard

    HAS_ZSTANDARD = True
except ImportError:
    HAS_ZSTANDARD = False


def decompress_zstd(data: bytes) -> bytes:
    if HAS_ZSTANDARD:
        return zstandard.ZstdDecompressor().decompress(data)

    for libname in ("libzstd.so.1", "libzstd.so", "libzstd.dylib", "zstd.dll"):
        try:
            lib = ctypes.CDLL(libname)
            break
        except OSError:
            continue
    else:
        raise RuntimeError("Could not find a Zstandard decompressor. Install with: pip install zstandard")

    lib.ZSTD_getDecompressedSize.restype = ctypes.c_uint64
    lib.ZSTD_getDecompressedSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]

    src = ctypes.create_string_buffer(data)
    size = lib.ZSTD_getDecompressedSize(src, len(data))
    if size == 0 or size > 500_000_000:
        size = 10_000_000

    dst = ctypes.create_string_buffer(size)
    n = lib.ZSTD_decompress(dst, size, src, len(data))
    if lib.ZSTD_isError(n):
        raise RuntimeError("Zstandard decompression failed.")
    return bytes(dst)[:n]


def load_spec_file(file_path: pathlib.Path) -> Optional[Dict]:
    try:
        raw = file_path.read_bytes()
        if raw[:4] == b'\x28\xb5\x2f\xfd':
            raw = decompress_zstd(raw)
        obj = json.loads(raw.decode("utf-8"))
        return obj.get("specification", obj)
    except Exception:
        return None


def extract_vehicle_info(spec: Dict) -> Dict:
    bc = spec.get("basicCharacteristics", {})

    def loc(obj, fallback: str = ""):
        if obj is None:
            return fallback
        if isinstance(obj, str):
            return obj or fallback
        if isinstance(obj, dict):
            return obj.get("message") or obj.get("handle") or fallback
        return str(obj) or fallback

    return {
        "display_name": loc(spec.get("vehicleName"), ""),
        "call_sign": loc(spec.get("callSign"), ""),
        "technical_name": spec.get("technicalName", ""),
        "statistics": {
            "lethality": bc.get("lethality", 0),
            "mobility": bc.get("mobility", 0),
            "survivability": bc.get("survivability", 0),
            "utility": bc.get("utility", 0)
        }
    }


def find_and_extract_spec_files(source_dir: str, temp_dir: str) -> List[pathlib.Path]:
    assets_dir = os.path.join(source_dir, ".assets", "output")

    if not os.path.exists(assets_dir):
        print(f"ERROR: Could not find .assets/output at {source_dir}")
        return []

    zip_files = [f for f in os.listdir(assets_dir) if f.lower().endswith(".zip")]
    if not zip_files:
        print("ERROR: No ZIP files found.")
        return []

    extracted_specs = []
    os.makedirs(temp_dir, exist_ok=True)

    for zip_file in zip_files:
        zip_path = os.path.join(assets_dir, zip_file)
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                specs_in_zip = [item for item in zip_ref.namelist() if item.lower().endswith(".specs")]
                for spec_path in specs_in_zip:
                    try:
                        extracted_path = zip_ref.extract(spec_path, temp_dir)
                        extracted_specs.append(pathlib.Path(extracted_path))
                    except Exception:
                        continue
        except Exception:
            continue

    return extracted_specs


def create_technical_name_index(spec_files: List[pathlib.Path]) -> Dict[str, Dict]:
    index = {}

    for spec_file in spec_files:
        spec_data = load_spec_file(spec_file)
        if not spec_data:
            continue

        vehicle_info = extract_vehicle_info(spec_data)

        if not vehicle_info["display_name"] and not vehicle_info["call_sign"]:
            continue

        tech_name = vehicle_info["technical_name"]
        if tech_name:
            index[tech_name] = vehicle_info

    return index


def create_tank_technical_mapping(tanks_json_path: str, script_dir: str) -> Dict[str, int]:
    mapping_file = os.path.join(script_dir, "technical_name_mapping.json")

    # Load existing mapping if it exists
    if os.path.exists(mapping_file):
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print("\nCreating technical name mapping index...")
    print("This file will be saved as 'technical_name_mapping.json' for future use.")

    # Load tanks to get their names
    with open(tanks_json_path, "r", encoding="utf-8") as f:
        tanks = json.load(f)

    # Common name to technical name
    manual_mapping = {
        "XM1-V": "a01_chrysler_xm1_volcano",
        "M1 Railgun": "a10_m1_railgun",
        "M3A1 Bradley": "a08_m3_bradley",
        "M60A1": "a14_m60a1",
        "M60A2": "a20_m60a2",
        "M60A3E2": "a03_m60a3",
        "M60A3E2 Bot": "a03_m60a3",
        "M551A1": "a05_m551a1_sheridan",
        "HSTV-L": "a07_hstv_l",
        "AGDS": "a11_agds",
        "XM1-90": "a13_xm1_90",
        "M1150 ABV": "a17_m110_abv",
        "M1E1": "a02_m1e1_120",
        "ALVT": "a12_alvt",
        "FV 4030/X": "gb01_challenger",
        "PTZ-89C": "ch_01_ptz89",
        "AMX-10 RC": "f05_amx_10_rc",
        "Leopard 1A1B": "g05_leopard_1_a1",
        "Leopard 1A6A1": "g01_leopard_1_a6_120",
        "Leopard 2K14": "g02_leopard2k_t14",
        "Leopard 2FK": "g06_leopard2fk_atgm",
        "Marder 1A3": "g07_marder1a3",
        "Object 279": "r06_object_279",
        "Object 287": "r08_object_287",
        "T-62AV": "r01_t_62a",
        "T-72AU": "r02_t_72a",
        "T-64A": "r05_t_64b",
        "BAT-4M": "r10_bat_4m_eneysp",
        "T-62MS": "r13_t_62m",
    }

    # Create mapping from tank name to ID
    name_to_id = {}
    for tank in tanks:
        name_to_id[tank["name"].upper()] = tank["id"]
        name_to_id[tank["slug"].upper().replace("-", " ")] = tank["id"]

    # Build the technical name to tank ID mapping
    result = {}
    for tank_name, tech_name in manual_mapping.items():
        tank_name_upper = tank_name.upper()
        if tank_name_upper in name_to_id:
            result[tech_name] = name_to_id[tank_name_upper]
            print(f"  Mapped: {tech_name} -> {tank_name} (ID: {name_to_id[tank_name_upper]})")
        else:
            print(f"  Warning: Could not find tank '{tank_name}' in tanks.json")

    # Save the mapping for future use
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"\nMapping saved to: {mapping_file}")
    return result


def update_tanks_json(tanks_json_path: str, game_vehicles: Dict[str, Dict], tech_to_tank_id: Dict[str, int],
                      script_dir: str) -> bool:
    if not os.path.exists(tanks_json_path):
        print(f"ERROR: tanks.json not found at {tanks_json_path}")
        return False

    with open(tanks_json_path, "r", encoding="utf-8") as f:
        tanks = json.load(f)

    # Create a lookup by ID for quick updates
    tank_by_id = {tank["id"]: tank for tank in tanks}

    matched_count = 0
    updated_count = 0
    unmatched_vehicles = []

    print("\nMatching vehicles by technical name...")

    # Match game vehicles to tanks using technical name mapping
    for tech_name, vehicle_info in game_vehicles.items():
        if tech_name in tech_to_tank_id:
            tank_id = tech_to_tank_id[tech_name]
            if tank_id in tank_by_id:
                matched_count += 1
                tank = tank_by_id[tank_id]

                # Skip bot vehicles with all zero stats
                if vehicle_info["statistics"]["lethality"] == 0 and \
                        vehicle_info["statistics"]["mobility"] == 0 and \
                        vehicle_info["statistics"]["survivability"] == 0 and \
                        vehicle_info["statistics"]["utility"] == 0:
                    continue

                # Update stats if different
                if tank.get("statistics", {}) != vehicle_info["statistics"]:
                    tank["statistics"] = vehicle_info["statistics"]
                    updated_count += 1
                    print(f"  Updated: {tank['name']} ({tech_name})")
        else:
            # Store unmatched vehicles for manual review
            if vehicle_info["statistics"]["lethality"] != 0 or \
                    vehicle_info["statistics"]["mobility"] != 0 or \
                    vehicle_info["statistics"]["survivability"] != 0 or \
                    vehicle_info["statistics"]["utility"] != 0:
                unmatched_vehicles.append(vehicle_info)

    # Save updated tanks.json
    with open(tanks_json_path, "w", encoding="utf-8") as f:
        json.dump(tanks, f, indent=4, ensure_ascii=False)

    print(f"\nMatched: {matched_count}/{len(game_vehicles)} game vehicles")
    print(f"Updated: {updated_count} tanks")

    if unmatched_vehicles:
        print(f"Unmatched game vehicles: {len(unmatched_vehicles)}")
        unmatched_path = os.path.join(script_dir, "unmatched_game_vehicles.json")
        with open(unmatched_path, "w", encoding="utf-8") as f:
            json.dump(unmatched_vehicles, f, indent=4, ensure_ascii=False)
        print(f"Unmatched vehicles saved to: {unmatched_path}")

    return True


def cleanup_temp_files(temp_dir: str):
    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    print("HEAT Labs - Vehicle Statistics Updater\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_tanks_json = os.path.join(script_dir, "..", "..", "HEAT-Labs-Configs", "tanks.json")

    source_dir = input("Project CW installation path: ").strip().strip("\"'")
    while not os.path.exists(source_dir) or not os.path.exists(os.path.join(source_dir, ".assets", "output")):
        print("Invalid path. Please enter the correct Project CW installation path.")
        source_dir = input("Project CW installation path: ").strip().strip("\"'")

    tanks_json_path = input(f"Tanks JSON path (Enter for default): ").strip().strip("\"'")
    if not tanks_json_path:
        tanks_json_path = default_tanks_json

    temp_dir = os.path.join(os.path.dirname(tanks_json_path) if os.path.dirname(tanks_json_path) else ".",
                            "__temp_specs__")

    print("\nProcessing...")

    # Extract spec files
    spec_files = find_and_extract_spec_files(source_dir, temp_dir)
    if not spec_files:
        print("ERROR: No .specs files found.")
        cleanup_temp_files(temp_dir)
        input("\nPress Enter to exit.")
        return

    # Create index of game vehicles by technical name
    game_vehicles = create_technical_name_index(spec_files)
    print(f"Found {len(game_vehicles)} vehicles in game files")

    # Create mapping between technical names and tank IDs
    tech_to_tank_id = create_tank_technical_mapping(tanks_json_path, script_dir)

    # Update tanks.json with matched stats
    success = update_tanks_json(tanks_json_path, game_vehicles, tech_to_tank_id, script_dir)

    cleanup_temp_files(temp_dir)

    print("\n" + ("SUCCESS!" if success else "FAILED!"))
    input("\nPress Enter to exit.")


if __name__ == "__main__":
    try:
        import shutil

        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        input()