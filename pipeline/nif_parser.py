"""
Step 3: Morrowind NIF parser (NetImmerse File Format v4.0.0.2).

Parses NIF files directly via struct — pyffi doesn't support v4 well on Python 3.12.
Extracts mesh geometry, skeleton, and skin weights needed for EGG conversion.
"""
import struct
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Matrix33:
    rows: List[List[float]] = field(default_factory=lambda: [[1,0,0],[0,1,0],[0,0,1]])


@dataclass
class NiNodeData:
    """Skeleton joint / scene node."""
    name: str = ""
    translation: Vector3 = field(default_factory=Vector3)
    rotation: Matrix33 = field(default_factory=Matrix33)
    scale: float = 1.0
    children_indices: List[int] = field(default_factory=list)
    children: List['NiNodeData'] = field(default_factory=list)
    block_index: int = -1


@dataclass
class SkinWeight:
    vertex_index: int = 0
    weight: float = 0.0


@dataclass
class BoneData:
    bone_name: str = ""
    bone_index: int = -1  # index into NIF block list
    offset_translation: Vector3 = field(default_factory=Vector3)
    offset_rotation: Matrix33 = field(default_factory=Matrix33)
    offset_scale: float = 1.0
    weights: List[SkinWeight] = field(default_factory=list)


@dataclass
class MeshData:
    """Extracted mesh geometry."""
    name: str = ""
    vertices: List[Tuple[float,float,float]] = field(default_factory=list)
    normals: List[Tuple[float,float,float]] = field(default_factory=list)
    uvs: List[Tuple[float,float]] = field(default_factory=list)
    triangles: List[Tuple[int,int,int]] = field(default_factory=list)
    bone_weights: Dict[int, List[Tuple[str,float]]] = field(default_factory=dict)
    # vert_idx → [(bone_name, weight)]


@dataclass
class NifData:
    """Complete parsed NIF file."""
    meshes: List[MeshData] = field(default_factory=list)
    skeleton_root: Optional[NiNodeData] = None
    all_nodes: Dict[int, NiNodeData] = field(default_factory=dict)
    version: int = 0


class NifParser:
    """
    Minimal parser for NetImmerse File Format v4.0.0.2 (Morrowind).

    NIF v4 structure:
    - Header: magic string + version + num_blocks
    - Blocks: sequential, each prefixed by type name string
    - Block types: NiNode, NiTriShape, NiTriShapeData, NiSkinInstance, NiSkinData, etc.
    """

    def __init__(self, flip_uv_v: bool = True):
        self.flip_uv_v = flip_uv_v

    def parse(self, nif_path: str) -> NifData:
        """Parse a Morrowind NIF file."""
        result = NifData()

        try:
            with open(nif_path, 'rb') as f:
                data = f.read()
        except IOError as e:
            logger.warning(f"Cannot read {nif_path}: {e}")
            return result

        try:
            self._parse_data(data, result)
        except Exception as e:
            logger.warning(f"Failed to parse {nif_path}: {e}")

        return result

    def _parse_data(self, data: bytes, result: NifData):
        """Internal parse implementation."""
        pos = 0

        # Header line (null-terminated or newline-terminated)
        nl = data.index(b'\x0a', pos)
        header_str = data[pos:nl].decode('ascii', errors='replace')
        pos = nl + 1

        # Version (4 bytes LE)
        result.version = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        # Number of blocks
        num_blocks = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        # Parse blocks
        blocks = []  # (type_name, block_data_dict)
        block_positions = []

        for i in range(num_blocks):
            # Block type: length-prefixed string
            type_len = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            type_name = data[pos:pos+type_len].decode('ascii', errors='replace')
            pos += type_len

            block_start = pos
            try:
                block_data, pos = self._parse_block(type_name, data, pos, i)
                blocks.append((type_name, block_data))
            except Exception as e:
                logger.debug(f"Block {i} ({type_name}) parse failed: {e}")
                blocks.append((type_name, None))
                break  # Can't continue if we lost position

        # Build node tree and extract meshes
        self._build_result(blocks, result)

    def _read_string(self, data: bytes, pos: int) -> Tuple[str, int]:
        """Read length-prefixed string."""
        length = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        s = data[pos:pos+length].decode('ascii', errors='replace')
        pos += length
        return s, pos

    def _read_vector3(self, data: bytes, pos: int) -> Tuple[Vector3, int]:
        x, y, z = struct.unpack_from('<3f', data, pos)
        return Vector3(x, y, z), pos + 12

    def _read_matrix33(self, data: bytes, pos: int) -> Tuple[Matrix33, int]:
        rows = []
        for _ in range(3):
            row = list(struct.unpack_from('<3f', data, pos))
            rows.append(row)
            pos += 12
        return Matrix33(rows), pos

    def _parse_block(self, type_name: str, data: bytes, pos: int, block_idx: int) -> Tuple[dict, int]:
        """Parse a single NIF block. Returns (block_data, new_pos)."""

        if type_name == 'NiNode':
            return self._parse_ni_node(data, pos, block_idx)
        elif type_name == 'NiTriShape':
            return self._parse_ni_tri_shape(data, pos, block_idx)
        elif type_name == 'NiTriShapeData':
            return self._parse_ni_tri_shape_data(data, pos)
        elif type_name == 'NiSkinInstance':
            return self._parse_ni_skin_instance(data, pos)
        elif type_name == 'NiSkinData':
            return self._parse_ni_skin_data(data, pos)
        elif type_name in ('NiStringExtraData', 'NiTextKeyExtraData'):
            return self._parse_extra_data(data, pos)
        elif type_name == 'NiMaterialProperty':
            return self._parse_material_property(data, pos)
        elif type_name == 'NiTexturingProperty':
            return self._parse_texturing_property(data, pos)
        elif type_name == 'NiSourceTexture':
            return self._parse_source_texture(data, pos)
        elif type_name == 'NiAlphaProperty':
            return self._parse_alpha_property(data, pos)
        elif type_name == 'NiVertexColorProperty':
            return self._parse_vertex_color_property(data, pos)
        elif type_name == 'NiZBufferProperty':
            return self._parse_zbuffer_property(data, pos)
        elif type_name == 'NiSpecularProperty':
            return self._parse_specular_property(data, pos)
        elif type_name == 'NiStencilProperty':
            return self._parse_stencil_property(data, pos)
        elif type_name == 'RootCollisionNode':
            return self._parse_ni_node(data, pos, block_idx)
        else:
            # Unknown block — try to skip it intelligently
            raise ValueError(f"Unknown block type: {type_name}")

    def _parse_ni_node_common(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Parse common NiObjectNET + NiAVObject fields (shared by NiNode and NiTriShape).
        NIF v4.0.0.2 format — NO extra_count field, only extra_data_ref."""
        result = {}

        # NiObjectNET: name
        name, pos = self._read_string(data, pos)
        result['name'] = name

        # Extra data ref (-1 = none) — v4 has ONLY this, no extra_count
        extra_data = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        result['extra_data'] = extra_data

        # Controller ref
        controller = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        result['controller'] = controller

        # NiAVObject: flags
        flags = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        result['flags'] = flags

        # Transform
        translation, pos = self._read_vector3(data, pos)
        rotation, pos = self._read_matrix33(data, pos)
        scale = struct.unpack_from('<f', data, pos)[0]
        pos += 4
        result['translation'] = translation
        result['rotation'] = rotation
        result['scale'] = scale

        # Velocity (v4.0.0.2)
        velocity, pos = self._read_vector3(data, pos)

        # Properties
        num_properties = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        properties = list(struct.unpack_from(f'<{num_properties}i', data, pos))
        pos += num_properties * 4
        result['properties'] = properties

        # Bounding box flag
        has_bounding_box = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        if has_bounding_box:
            # center(3f) + rotation(9f) + extent(3f) = 60 bytes
            pos += 60

        return result, pos

    def _parse_ni_node(self, data: bytes, pos: int, block_idx: int) -> Tuple[dict, int]:
        """Parse NiNode (skeleton joint / scene node)."""
        result, pos = self._parse_ni_node_common(data, pos)
        result['block_type'] = 'NiNode'
        result['block_index'] = block_idx

        # Children
        num_children = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        children = list(struct.unpack_from(f'<{num_children}i', data, pos))
        pos += num_children * 4
        result['children_indices'] = children

        # Effects
        num_effects = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        pos += num_effects * 4  # skip effect refs

        return result, pos

    def _parse_ni_tri_shape(self, data: bytes, pos: int, block_idx: int) -> Tuple[dict, int]:
        """Parse NiTriShape (mesh reference)."""
        result, pos = self._parse_ni_node_common(data, pos)
        result['block_type'] = 'NiTriShape'
        result['block_index'] = block_idx

        # Data ref (NiTriShapeData)
        data_ref = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        result['data_ref'] = data_ref

        # Skin instance ref
        skin_ref = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        result['skin_ref'] = skin_ref

        return result, pos

    def _parse_ni_tri_shape_data(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Parse NiTriShapeData (actual mesh geometry)."""
        result = {'block_type': 'NiTriShapeData'}

        # Num vertices
        num_verts = struct.unpack_from('<H', data, pos)[0]
        pos += 2

        # Has vertices flag
        has_verts = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        vertices = []
        if has_verts and num_verts > 0:
            for _ in range(num_verts):
                x, y, z = struct.unpack_from('<3f', data, pos)
                vertices.append((x, y, z))
                pos += 12
        result['vertices'] = vertices

        # Has normals
        has_normals = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        normals = []
        if has_normals and num_verts > 0:
            for _ in range(num_verts):
                nx, ny, nz = struct.unpack_from('<3f', data, pos)
                normals.append((nx, ny, nz))
                pos += 12
        result['normals'] = normals

        # Center + radius (bounding sphere)
        pos += 16  # 3 floats + 1 float

        # Has vertex colors
        has_colors = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        if has_colors and num_verts > 0:
            pos += num_verts * 16  # 4 floats RGBA per vertex

        # UV sets
        num_uv_sets = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        # Has UV flag
        has_uv = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        uvs = []
        if has_uv and num_uv_sets > 0 and num_verts > 0:
            # Read first UV set
            for _ in range(num_verts):
                u, v = struct.unpack_from('<2f', data, pos)
                if self:
                    v = 1.0 - v  # Flip V for OpenGL
                uvs.append((u, v))
                pos += 8
            # Skip remaining UV sets
            for _ in range(num_uv_sets - 1):
                pos += num_verts * 8
        result['uvs'] = uvs

        # Triangles
        num_triangles = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        # Num triangle points (= num_triangles * 3)
        num_points = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        # Has triangles flag
        has_triangles = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        triangles = []
        if has_triangles and num_triangles > 0:
            for _ in range(num_triangles):
                i1, i2, i3 = struct.unpack_from('<3H', data, pos)
                triangles.append((i1, i2, i3))
                pos += 6
        result['triangles'] = triangles

        # Match groups (for strips — skip)
        num_match_groups = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        for _ in range(num_match_groups):
            num_matches = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            pos += num_matches * 2

        result['num_verts'] = num_verts
        return result, pos

    def _parse_ni_skin_instance(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Parse NiSkinInstance."""
        result = {'block_type': 'NiSkinInstance'}

        # Skin data ref
        skin_data_ref = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        result['skin_data_ref'] = skin_data_ref

        # Root node ref (skeleton root)
        root_ref = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        result['root_ref'] = root_ref

        # Bone refs
        num_bones = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        bone_refs = list(struct.unpack_from(f'<{num_bones}i', data, pos))
        pos += num_bones * 4
        result['bone_refs'] = bone_refs

        return result, pos

    def _parse_ni_skin_data(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Parse NiSkinData (bone weights)."""
        result = {'block_type': 'NiSkinData'}

        # Overall transform
        rotation, pos = self._read_matrix33(data, pos)
        translation, pos = self._read_vector3(data, pos)
        scale = struct.unpack_from('<f', data, pos)[0]
        pos += 4

        # Num bones
        num_bones = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        # Skin partition ref (v4 has this)
        partition_ref = struct.unpack_from('<i', data, pos)[0]
        pos += 4

        bones = []
        for _ in range(num_bones):
            bone = {}
            # Bone transform (offset)
            bone_rot, pos = self._read_matrix33(data, pos)
            bone_trans, pos = self._read_vector3(data, pos)
            bone_scale = struct.unpack_from('<f', data, pos)[0]
            pos += 4
            bone['rotation'] = bone_rot
            bone['translation'] = bone_trans
            bone['scale'] = bone_scale

            # Bounding sphere (center + radius)
            pos += 16

            # Vertex weights
            num_weights = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            weights = []
            for _ in range(num_weights):
                vert_idx = struct.unpack_from('<H', data, pos)[0]
                pos += 2
                weight = struct.unpack_from('<f', data, pos)[0]
                pos += 4
                weights.append(SkinWeight(vert_idx, weight))
            bone['weights'] = weights
            bones.append(bone)

        result['bones'] = bones
        return result, pos

    def _parse_extra_data(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Parse NiStringExtraData / NiTextKeyExtraData."""
        result = {'block_type': 'ExtraData'}
        # Next ref
        next_ref = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        # String data size
        str_size = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        # String
        s = data[pos:pos+str_size].decode('ascii', errors='replace')
        pos += str_size
        result['value'] = s
        return result, pos

    def _parse_material_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Skip NiMaterialProperty."""
        result = {'block_type': 'NiMaterialProperty'}
        name, pos = self._read_string(data, pos)
        result['name'] = name
        # Extra data + controller
        pos += 4 + 4 + 4  # extra_data, extra_count (0), controller
        # Flags
        pos += 2
        # Ambient, diffuse, specular, emissive (4 * 3 floats = 48 bytes)
        pos += 48
        # Glossiness, alpha
        pos += 8
        return result, pos

    def _parse_texturing_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Skip NiTexturingProperty (complex, just skip)."""
        result = {'block_type': 'NiTexturingProperty'}
        name, pos = self._read_string(data, pos)
        pos += 4  # extra_data ref
        pos += 4  # controller
        # Flags
        pos += 2
        # Apply mode
        pos += 4
        # Texture count
        tex_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        # Each texture entry
        for _ in range(tex_count):
            has_tex = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            if has_tex:
                # Source ref + clamp mode + filter mode + uv set
                pos += 4 + 4 + 4 + 4
                # PS2 fields (v4)
                pos += 2  # PS2 L
                pos += 2  # PS2 K
        return result, pos

    def _parse_source_texture(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Parse NiSourceTexture."""
        result = {'block_type': 'NiSourceTexture'}
        name, pos = self._read_string(data, pos)
        pos += 4  # extra_data ref (v4: no extra_count)
        pos += 4  # controller
        # External flag
        use_external = struct.unpack_from('<B', data, pos)[0]
        pos += 1
        if use_external:
            filename, pos = self._read_string(data, pos)
            result['filename'] = filename
            pos += 4  # unknown ref
        else:
            pos += 4  # internal texture data ref
            filename, pos = self._read_string(data, pos)
            result['filename'] = filename
        # Pixel layout + mipmap + alpha format
        pos += 4 + 4 + 4
        return result, pos

    def _parse_alpha_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        result = {'block_type': 'NiAlphaProperty'}
        name, pos = self._read_string(data, pos)
        pos += 4  # extra_data ref (v4: no extra_count)
        pos += 4  # controller
        pos += 2  # flags
        pos += 1  # threshold
        return result, pos

    def _parse_vertex_color_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        result = {'block_type': 'NiVertexColorProperty'}
        name, pos = self._read_string(data, pos)
        pos += 4  # extra_data ref (v4: no extra_count)
        pos += 4  # controller
        pos += 2  # flags
        pos += 4 + 4  # source vertex mode, lighting mode
        return result, pos

    def _parse_zbuffer_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        result = {'block_type': 'NiZBufferProperty'}
        name, pos = self._read_string(data, pos)
        pos += 4  # extra_data ref (v4: no extra_count)
        pos += 4  # controller
        pos += 2  # flags
        return result, pos

    def _parse_specular_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        result = {'block_type': 'NiSpecularProperty'}
        name, pos = self._read_string(data, pos)
        pos += 4
        extra_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4 + extra_count * 4
        pos += 4
        pos += 2  # flags
        return result, pos

    def _parse_stencil_property(self, data: bytes, pos: int) -> Tuple[dict, int]:
        result = {'block_type': 'NiStencilProperty'}
        name, pos = self._read_string(data, pos)
        pos += 4
        extra_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4 + extra_count * 4
        pos += 4
        pos += 2  # flags
        # Stencil enabled, func, ref, mask, fail action, z fail, pass action, draw mode
        pos += 1 + 4 + 4 + 4 + 4 + 4 + 4 + 4
        return result, pos

    def _build_result(self, blocks: list, result: NifData):
        """Build NifData from parsed blocks."""
        # Index nodes and shapes
        nodes = {}  # block_idx -> NiNodeData
        shapes = {}  # block_idx -> shape dict
        shape_data = {}  # block_idx -> NiTriShapeData dict
        skin_instances = {}  # block_idx -> skin instance dict
        skin_data_blocks = {}  # block_idx -> skin data dict

        for i, (type_name, bdata) in enumerate(blocks):
            if bdata is None:
                continue
            bt = bdata.get('block_type', type_name)

            if bt == 'NiNode':
                node = NiNodeData(
                    name=bdata['name'],
                    translation=bdata['translation'],
                    rotation=bdata['rotation'],
                    scale=bdata['scale'],
                    children_indices=bdata.get('children_indices', []),
                    block_index=i,
                )
                nodes[i] = node
                result.all_nodes[i] = node

            elif bt == 'NiTriShape':
                shapes[i] = bdata

            elif bt == 'NiTriShapeData':
                shape_data[i] = bdata

            elif bt == 'NiSkinInstance':
                skin_instances[i] = bdata

            elif bt == 'NiSkinData':
                skin_data_blocks[i] = bdata

        # Build node tree
        for idx, node in nodes.items():
            for child_idx in node.children_indices:
                if child_idx in nodes:
                    node.children.append(nodes[child_idx])

        # Find skeleton root (first node named "Bip01" or root node)
        for idx, node in nodes.items():
            if 'bip01' in node.name.lower() and node.name.lower().strip() == 'bip01':
                result.skeleton_root = node
                break
        if not result.skeleton_root and nodes:
            # Fallback: first root-level node
            result.skeleton_root = list(nodes.values())[0]

        # Extract meshes
        for shape_idx, shape in shapes.items():
            data_ref = shape.get('data_ref', -1)
            if data_ref < 0 or data_ref not in shape_data:
                continue

            sd = shape_data[data_ref]
            mesh = MeshData(
                name=shape.get('name', f'mesh_{shape_idx}'),
                vertices=sd.get('vertices', []),
                normals=sd.get('normals', []),
                uvs=sd.get('uvs', []),
                triangles=sd.get('triangles', []),
            )

            # Extract skin weights if present
            skin_ref = shape.get('skin_ref', -1)
            if skin_ref >= 0 and skin_ref in skin_instances:
                skin_inst = skin_instances[skin_ref]
                skin_data_ref = skin_inst.get('skin_data_ref', -1)
                bone_refs = skin_inst.get('bone_refs', [])

                if skin_data_ref >= 0 and skin_data_ref in skin_data_blocks:
                    sd_block = skin_data_blocks[skin_data_ref]
                    bones_data = sd_block.get('bones', [])

                    for bone_i, bone_info in enumerate(bones_data):
                        # Get bone name from node
                        if bone_i < len(bone_refs):
                            bone_node_idx = bone_refs[bone_i]
                            bone_name = ""
                            if bone_node_idx in nodes:
                                bone_name = nodes[bone_node_idx].name
                            elif bone_node_idx in shapes:
                                bone_name = shapes[bone_node_idx].get('name', '')

                            if not bone_name:
                                bone_name = f"bone_{bone_i}"

                            for sw in bone_info.get('weights', []):
                                if sw.weight > 0.001:
                                    if sw.vertex_index not in mesh.bone_weights:
                                        mesh.bone_weights[sw.vertex_index] = []
                                    mesh.bone_weights[sw.vertex_index].append(
                                        (bone_name, sw.weight)
                                    )

            if mesh.vertices:
                result.meshes.append(mesh)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    test_nif = sys.argv[1] if len(sys.argv) > 1 else \
        'morrowind_content/bsa_extracted/meshes/b/b_n_dark elf_m_skins.nif'

    parser = NifParser(flip_uv_v=True)
    result = parser.parse(test_nif)

    print(f"\nVersion: 0x{result.version:08X}")
    print(f"Skeleton root: {result.skeleton_root.name if result.skeleton_root else 'None'}")
    print(f"Nodes: {len(result.all_nodes)}")
    print(f"Meshes: {len(result.meshes)}")

    for mesh in result.meshes:
        print(f"  Mesh '{mesh.name}': {len(mesh.vertices)} verts, "
              f"{len(mesh.triangles)} tris, "
              f"{len(mesh.uvs)} uvs, "
              f"{len(mesh.bone_weights)} skinned verts")

    if result.skeleton_root:
        def print_skel(node, indent=0):
            print(f"{'  '*indent}Joint: {node.name}")
            for child in node.children:
                print_skel(child, indent+1)
        print("\nSkeleton:")
        print_skel(result.skeleton_root)
