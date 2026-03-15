"""
Step 2: Extract NIF/KF/DDS/TGA files from Morrowind BSA archives.
"""
import os
import struct
import logging

logger = logging.getLogger(__name__)

# BSA format constants (Morrowind BSA)
BSA_MAGIC = 0x00000100


def extract_bsa(config: dict):
    """Extract mesh/animation/texture files from Morrowind BSA archives."""
    data_dir = config['morrowind']['data_dir']
    bsa_files = config['morrowind']['bsa_files']
    extract_dir = config['pipeline']['extract_dir']

    os.makedirs(extract_dir, exist_ok=True)

    wanted_exts = {'.nif', '.kf', '.dds', '.tga'}

    for bsa_name in bsa_files:
        bsa_path = os.path.join(data_dir, bsa_name)
        if not os.path.exists(bsa_path):
            logger.warning(f"BSA not found: {bsa_path}")
            continue

        logger.info(f"[BSA] Opening {bsa_name}...")
        _extract_morrowind_bsa(bsa_path, extract_dir, wanted_exts)


def _extract_morrowind_bsa(bsa_path: str, extract_dir: str, wanted_exts: set):
    """
    Extract files from Morrowind BSA format.

    Morrowind BSA header:
    - 4 bytes: version (0x100)
    - 4 bytes: hash_table_offset
    - 4 bytes: file_count
    Then file_count records of:
    - 4 bytes: file_size
    - 4 bytes: file_offset (from data start)
    Then name_offset_table, name_table, hash_table.
    """
    with open(bsa_path, 'rb') as f:
        # Header
        version = struct.unpack('<I', f.read(4))[0]
        if version != BSA_MAGIC:
            logger.error(f"Not a Morrowind BSA: version=0x{version:08X}")
            return

        hash_offset = struct.unpack('<I', f.read(4))[0]
        file_count = struct.unpack('<I', f.read(4))[0]

        logger.info(f"[BSA] {file_count} files, hash_offset={hash_offset}")

        # File size/offset records
        file_records = []
        for _ in range(file_count):
            fsize = struct.unpack('<I', f.read(4))[0]
            foffset = struct.unpack('<I', f.read(4))[0]
            file_records.append((fsize, foffset))

        # Name offset table
        name_offsets = []
        for _ in range(file_count):
            noff = struct.unpack('<I', f.read(4))[0]
            name_offsets.append(noff)

        # Name table — null-terminated strings
        names_start = f.tell()
        # Read all names at once
        names_block_size = hash_offset - (names_start - 12)
        names_block = f.read(names_block_size)

        file_names = []
        for noff in name_offsets:
            # Find null terminator
            end = names_block.index(b'\x00', noff)
            name = names_block[noff:end].decode('ascii', errors='replace')
            file_names.append(name)

        # Data starts after hash table
        data_start = 12 + file_count * 12 + names_block_size + file_count * 8

        # Extract wanted files
        extracted = 0
        skipped = 0
        for i, (fsize, foffset) in enumerate(file_records):
            name = file_names[i]
            ext = os.path.splitext(name)[1].lower()

            if ext not in wanted_exts:
                continue

            out_path = os.path.join(extract_dir, name.replace('\\', '/'))

            if os.path.exists(out_path) and os.path.getsize(out_path) == fsize:
                skipped += 1
                continue

            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            f.seek(data_start + foffset)
            data = f.read(fsize)

            with open(out_path, 'wb') as out:
                out.write(data)

            extracted += 1

        logger.info(f"[BSA] Extracted {extracted} files, skipped {skipped} (cached)")


if __name__ == "__main__":
    import yaml
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    with open('pipeline/config.yaml') as f:
        config = yaml.safe_load(f)

    extract_bsa(config)
