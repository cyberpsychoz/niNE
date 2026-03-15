"""
Scan extracted Morrowind meshes and catalog body parts, heads, hair, and animations.
Produces a report of available assets for slot_map.py.
"""
import os
import re
import yaml
import json
from collections import defaultdict


def scan_body_parts(extract_dir: str) -> dict:
    """Scan meshes/b/ for body part NIFs, categorize by race/gender/part."""
    meshes_b = os.path.join(extract_dir, 'meshes', 'b')
    if not os.path.isdir(meshes_b):
        print(f"ERROR: {meshes_b} not found")
        return {}

    # Pattern: b_n_<race>_<gender>_<part>.nif
    # race can have spaces: "dark elf", "high elf", "wood elf"
    pattern = re.compile(
        r'b_n_(.+?)_(m|f)_(.+?)\.nif$',
        re.IGNORECASE
    )

    catalog = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    # catalog[race][gender][part_type] = [file_paths]

    for fname in sorted(os.listdir(meshes_b)):
        if not fname.lower().endswith('.nif'):
            continue

        m = pattern.match(fname.lower())
        if not m:
            continue

        race = m.group(1).strip()
        gender = m.group(2)
        part = m.group(3).strip()

        # Categorize part type
        part_type = _classify_part(part)
        rel_path = os.path.join('meshes', 'b', fname)
        catalog[race][gender][part_type].append(rel_path)

    return dict(catalog)


def _classify_part(part_name: str) -> str:
    """Classify a body part name into a category."""
    part = part_name.lower()
    if 'head' in part and 'hair' not in part:
        return 'head'
    if 'hair' in part:
        return 'hair'
    if 'skins' in part or 'chest' in part:
        return 'body'
    if 'hands' in part:
        return 'hands'
    if 'foot' in part or 'feet' in part or 'ankle' in part:
        return 'feet'
    if 'upper arm' in part or 'forearm' in part or 'wrist' in part:
        return 'arms'
    if 'upper leg' in part or 'knee' in part or 'groin' in part:
        return 'legs'
    if 'neck' in part:
        return 'neck'
    return 'other'


def scan_animations(extract_dir: str) -> dict:
    """Scan for KF animation files."""
    meshes_dir = os.path.join(extract_dir, 'meshes')
    anims = {}

    for root, dirs, files in os.walk(meshes_dir):
        for fname in files:
            if fname.lower().endswith('.kf'):
                rel = os.path.relpath(os.path.join(root, fname), extract_dir)
                anims[fname.lower()] = rel

    return anims


def scan_base_anims(extract_dir: str) -> list:
    """List animation files specifically for base character anims."""
    meshes_dir = os.path.join(extract_dir, 'meshes')
    base_anims = []
    for fname in os.listdir(meshes_dir):
        if fname.lower().startswith('xbase_anim') and fname.lower().endswith('.kf'):
            base_anims.append(os.path.join('meshes', fname))
    return sorted(base_anims)


def print_catalog(catalog: dict, anims: dict, base_anims: list):
    """Print formatted catalog."""
    print("=" * 60)
    print("MORROWIND BODY PARTS CATALOG")
    print("=" * 60)

    races = sorted(catalog.keys())
    for race in races:
        print(f"\n--- {race.upper()} ---")
        for gender in sorted(catalog[race].keys()):
            g_label = "Male" if gender == 'm' else "Female"
            print(f"  {g_label}:")
            for part_type in sorted(catalog[race][gender].keys()):
                files = catalog[race][gender][part_type]
                print(f"    {part_type:10s}: {len(files)} files")
                for f in files[:3]:
                    print(f"      {os.path.basename(f)}")
                if len(files) > 3:
                    print(f"      ... +{len(files)-3} more")

    print(f"\n{'=' * 60}")
    print(f"ANIMATIONS")
    print(f"{'=' * 60}")
    print(f"Base animations: {len(base_anims)}")
    for a in base_anims:
        print(f"  {a}")
    print(f"Total KF files: {len(anims)}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"Races: {len(races)}")
    for race in races:
        genders = list(catalog[race].keys())
        print(f"  {race}: {', '.join('M' if g=='m' else 'F' for g in genders)}")


if __name__ == "__main__":
    with open('pipeline/config.yaml') as f:
        config = yaml.safe_load(f)

    extract_dir = config['pipeline']['extract_dir']

    catalog = scan_body_parts(extract_dir)
    anims = scan_animations(extract_dir)
    base_anims = scan_base_anims(extract_dir)

    print_catalog(catalog, anims, base_anims)

    # Save catalog as JSON for other scripts
    with open('pipeline/build/body_catalog.json', 'w') as f:
        json.dump({
            'body_parts': {race: {g: {pt: files for pt, files in parts.items()}
                                   for g, parts in genders.items()}
                           for race, genders in catalog.items()},
            'base_anims': base_anims,
            'total_kf': len(anims),
        }, f, indent=2)
    print(f"\nCatalog saved to pipeline/build/body_catalog.json")
