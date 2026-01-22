"""
Spatial partitioning system for niNE.

Provides grid-based spatial hashing for fast neighbor queries.
Used for:
- AI enemy detection (O(k) instead of O(n))
- Interest management (determining which NPCs to send to clients)
- Collision broad-phase (if needed)

Performance:
- Insert/Update: O(1)
- Remove: O(1)
- Range query: O(k) where k = number of cells in range

Example usage:
    spatial = SpatialHash(cell_size=10.0)

    # Update entity positions
    spatial.update_entity("npc_1", x=15.0, y=20.0)
    spatial.update_entity("npc_2", x=12.0, y=18.0)

    # Query nearby entities
    nearby = spatial.get_nearby_entities(x=10.0, y=15.0, radius=15.0)
    # Returns: ["npc_1", "npc_2"]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Set, List, Tuple, Optional, Iterator
import logging

logger = logging.getLogger(__name__)


@dataclass
class SpatialCell:
    """
    A cell in the spatial grid.

    Attributes:
        entities: Set of entity IDs currently in this cell
        x: Cell X coordinate (grid space)
        y: Cell Y coordinate (grid space)
    """
    x: int
    y: int
    entities: Set[str] = field(default_factory=set)


class SpatialHash:
    """
    Grid-based spatial partitioning for fast neighbor queries.

    Divides the world into cells of fixed size. Each entity is assigned
    to a cell based on its position. Neighbor queries only check cells
    that overlap with the query radius.

    Thread Safety:
        This class is NOT thread-safe. If using from multiple threads,
        external synchronization is required.
    """

    def __init__(self, cell_size: float = 10.0):
        """
        Initialize spatial hash.

        Args:
            cell_size: Size of each cell in world units.
                       Larger cells = fewer cells to check but more entities per cell.
                       Recommended: 2-3x the typical query radius.
        """
        self.cell_size = cell_size
        self._inv_cell_size = 1.0 / cell_size  # Cache for faster division

        # Cell storage: (cell_x, cell_y) -> SpatialCell
        self._cells: Dict[Tuple[int, int], SpatialCell] = {}

        # Entity tracking: entity_id -> (cell_x, cell_y)
        self._entity_cells: Dict[str, Tuple[int, int]] = {}

        # Statistics for debugging/profiling
        self._stats = {
            "updates": 0,
            "queries": 0,
            "total_entities": 0,
        }

        logger.debug(f"SpatialHash initialized with cell_size={cell_size}")

    # =========================================================================
    # Core Operations
    # =========================================================================

    def update_entity(self, entity_id: str, x: float, y: float) -> None:
        """
        Update entity position in the grid.

        If the entity moves to a new cell, it's removed from the old cell
        and added to the new one. If it stays in the same cell, this is
        essentially a no-op.

        Args:
            entity_id: Unique identifier for the entity
            x: World X coordinate
            y: World Y coordinate

        Complexity: O(1) average case
        """
        new_cell = self._world_to_cell(x, y)
        old_cell = self._entity_cells.get(entity_id)

        # Entity hasn't moved to a new cell
        if old_cell == new_cell:
            return

        # Remove from old cell
        if old_cell is not None:
            self._remove_from_cell(entity_id, old_cell)
        else:
            # New entity
            self._stats["total_entities"] += 1

        # Add to new cell
        self._add_to_cell(entity_id, new_cell)
        self._entity_cells[entity_id] = new_cell

        self._stats["updates"] += 1

    def remove_entity(self, entity_id: str) -> bool:
        """
        Remove entity from the grid.

        Args:
            entity_id: Unique identifier for the entity

        Returns:
            True if entity was found and removed, False otherwise

        Complexity: O(1)
        """
        cell_coords = self._entity_cells.pop(entity_id, None)
        if cell_coords is None:
            return False

        self._remove_from_cell(entity_id, cell_coords)
        self._stats["total_entities"] -= 1
        return True

    def get_nearby_entities(
        self,
        x: float,
        y: float,
        radius: float,
        exclude_entity: Optional[str] = None
    ) -> List[str]:
        """
        Get all entities within radius of a point.

        This is an approximation - it returns all entities in cells that
        overlap with the query circle. For exact distance checking, the
        caller should verify distances.

        Args:
            x: Query center X coordinate
            y: Query center Y coordinate
            radius: Search radius in world units
            exclude_entity: Optional entity ID to exclude from results

        Returns:
            List of entity IDs in the area (unordered)

        Complexity: O(k * m) where k = cells checked, m = avg entities per cell
        """
        self._stats["queries"] += 1
        result = []

        # Calculate which cells overlap with the query circle
        min_cell_x, min_cell_y = self._world_to_cell(x - radius, y - radius)
        max_cell_x, max_cell_y = self._world_to_cell(x + radius, y + radius)

        # Check each overlapping cell
        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1):
                cell = self._cells.get((cell_x, cell_y))
                if cell:
                    for entity_id in cell.entities:
                        if entity_id != exclude_entity:
                            result.append(entity_id)

        return result

    def get_nearby_entities_with_distances(
        self,
        x: float,
        y: float,
        radius: float,
        positions: Dict[str, Tuple[float, float]],
        exclude_entity: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Get nearby entities with their exact distances.

        Unlike get_nearby_entities(), this performs exact distance checks
        and returns entities sorted by distance.

        Args:
            x, y: Query center coordinates
            radius: Search radius
            positions: Dict mapping entity_id -> (x, y) position
            exclude_entity: Optional entity to exclude

        Returns:
            List of (entity_id, distance) tuples, sorted by distance
        """
        candidates = self.get_nearby_entities(x, y, radius, exclude_entity)
        results = []

        radius_sq = radius * radius

        for entity_id in candidates:
            pos = positions.get(entity_id)
            if pos is None:
                continue

            dx = pos[0] - x
            dy = pos[1] - y
            dist_sq = dx * dx + dy * dy

            if dist_sq <= radius_sq:
                results.append((entity_id, math.sqrt(dist_sq)))

        results.sort(key=lambda t: t[1])
        return results

    def get_entities_in_cell(self, cell_x: int, cell_y: int) -> Set[str]:
        """
        Get all entities in a specific cell.

        Args:
            cell_x: Cell X coordinate
            cell_y: Cell Y coordinate

        Returns:
            Set of entity IDs (may be empty)
        """
        cell = self._cells.get((cell_x, cell_y))
        if cell:
            return cell.entities.copy()
        return set()

    def get_entities_in_rect(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float
    ) -> List[str]:
        """
        Get all entities in a rectangular area.

        Args:
            min_x, min_y: Minimum corner
            max_x, max_y: Maximum corner

        Returns:
            List of entity IDs in the area
        """
        result = []

        min_cell_x, min_cell_y = self._world_to_cell(min_x, min_y)
        max_cell_x, max_cell_y = self._world_to_cell(max_x, max_y)

        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1):
                cell = self._cells.get((cell_x, cell_y))
                if cell:
                    result.extend(cell.entities)

        return result

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_entity_cell(self, entity_id: str) -> Optional[Tuple[int, int]]:
        """
        Get the cell coordinates for an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            (cell_x, cell_y) or None if entity not tracked
        """
        return self._entity_cells.get(entity_id)

    def contains_entity(self, entity_id: str) -> bool:
        """Check if entity is tracked in the spatial hash."""
        return entity_id in self._entity_cells

    def clear(self) -> None:
        """Remove all entities from the spatial hash."""
        self._cells.clear()
        self._entity_cells.clear()
        self._stats["total_entities"] = 0
        logger.debug("SpatialHash cleared")

    def get_all_entities(self) -> Iterator[str]:
        """Iterate over all tracked entity IDs."""
        return iter(self._entity_cells.keys())

    @property
    def entity_count(self) -> int:
        """Number of entities currently tracked."""
        return len(self._entity_cells)

    @property
    def cell_count(self) -> int:
        """Number of non-empty cells."""
        return len(self._cells)

    def get_stats(self) -> Dict:
        """
        Get performance statistics.

        Returns:
            Dict with stats (updates, queries, entity count, etc.)
        """
        return {
            **self._stats,
            "cell_count": self.cell_count,
            "cell_size": self.cell_size,
            "avg_entities_per_cell": (
                self._stats["total_entities"] / self.cell_count
                if self.cell_count > 0 else 0
            )
        }

    def reset_stats(self) -> None:
        """Reset statistics counters (keeps entity count)."""
        self._stats["updates"] = 0
        self._stats["queries"] = 0

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to cell coordinates."""
        return (
            int(math.floor(x * self._inv_cell_size)),
            int(math.floor(y * self._inv_cell_size))
        )

    def _cell_to_world_center(self, cell_x: int, cell_y: int) -> Tuple[float, float]:
        """Get world coordinates of cell center."""
        return (
            (cell_x + 0.5) * self.cell_size,
            (cell_y + 0.5) * self.cell_size
        )

    def _add_to_cell(self, entity_id: str, cell_coords: Tuple[int, int]) -> None:
        """Add entity to a cell, creating the cell if needed."""
        cell = self._cells.get(cell_coords)
        if cell is None:
            cell = SpatialCell(x=cell_coords[0], y=cell_coords[1])
            self._cells[cell_coords] = cell
        cell.entities.add(entity_id)

    def _remove_from_cell(self, entity_id: str, cell_coords: Tuple[int, int]) -> None:
        """Remove entity from a cell, deleting empty cells."""
        cell = self._cells.get(cell_coords)
        if cell:
            cell.entities.discard(entity_id)
            # Clean up empty cells to save memory
            if not cell.entities:
                del self._cells[cell_coords]


# =============================================================================
# Multi-Resolution Spatial Hash (for very large worlds)
# =============================================================================

class MultiResolutionSpatialHash:
    """
    Multi-resolution spatial hash for large worlds with varying entity densities.

    Uses multiple spatial hashes with different cell sizes:
    - Fine grid (small cells) for nearby queries
    - Coarse grid (large cells) for far queries

    This is useful when you have different query radii:
    - Combat: 30 units (use fine grid)
    - Interest management: 100 units (use coarse grid)
    """

    def __init__(
        self,
        fine_cell_size: float = 10.0,
        coarse_cell_size: float = 50.0
    ):
        """
        Initialize multi-resolution spatial hash.

        Args:
            fine_cell_size: Cell size for fine grid (nearby queries)
            coarse_cell_size: Cell size for coarse grid (far queries)
        """
        self.fine = SpatialHash(cell_size=fine_cell_size)
        self.coarse = SpatialHash(cell_size=coarse_cell_size)
        self._threshold = fine_cell_size * 3  # Use coarse grid for queries > this

    def update_entity(self, entity_id: str, x: float, y: float) -> None:
        """Update entity in both grids."""
        self.fine.update_entity(entity_id, x, y)
        self.coarse.update_entity(entity_id, x, y)

    def remove_entity(self, entity_id: str) -> bool:
        """Remove entity from both grids."""
        fine_removed = self.fine.remove_entity(entity_id)
        coarse_removed = self.coarse.remove_entity(entity_id)
        return fine_removed or coarse_removed

    def get_nearby_entities(
        self,
        x: float,
        y: float,
        radius: float,
        exclude_entity: Optional[str] = None
    ) -> List[str]:
        """
        Get nearby entities using the appropriate grid.

        Automatically selects fine or coarse grid based on query radius.
        """
        if radius <= self._threshold:
            return self.fine.get_nearby_entities(x, y, radius, exclude_entity)
        else:
            return self.coarse.get_nearby_entities(x, y, radius, exclude_entity)

    def clear(self) -> None:
        """Clear both grids."""
        self.fine.clear()
        self.coarse.clear()

    @property
    def entity_count(self) -> int:
        """Number of tracked entities."""
        return self.fine.entity_count


# =============================================================================
# Spatial Query Helpers
# =============================================================================

def find_nearest_entity(
    x: float,
    y: float,
    spatial: SpatialHash,
    positions: Dict[str, Tuple[float, float]],
    max_radius: float,
    exclude_entity: Optional[str] = None,
    filter_fn: Optional[callable] = None
) -> Optional[Tuple[str, float]]:
    """
    Find the nearest entity to a point.

    Args:
        x, y: Query point
        spatial: Spatial hash to query
        positions: Dict mapping entity_id -> (x, y)
        max_radius: Maximum search radius
        exclude_entity: Entity to exclude
        filter_fn: Optional function(entity_id) -> bool to filter results

    Returns:
        (entity_id, distance) of nearest entity, or None if none found
    """
    results = spatial.get_nearby_entities_with_distances(
        x, y, max_radius, positions, exclude_entity
    )

    for entity_id, distance in results:
        if filter_fn is None or filter_fn(entity_id):
            return (entity_id, distance)

    return None


def count_entities_in_radius(
    x: float,
    y: float,
    radius: float,
    spatial: SpatialHash,
    positions: Dict[str, Tuple[float, float]]
) -> int:
    """
    Count entities within a radius (exact count with distance check).

    Args:
        x, y: Center point
        radius: Search radius
        spatial: Spatial hash
        positions: Entity positions

    Returns:
        Number of entities within radius
    """
    candidates = spatial.get_nearby_entities(x, y, radius)
    radius_sq = radius * radius
    count = 0

    for entity_id in candidates:
        pos = positions.get(entity_id)
        if pos:
            dx = pos[0] - x
            dy = pos[1] - y
            if dx * dx + dy * dy <= radius_sq:
                count += 1

    return count
