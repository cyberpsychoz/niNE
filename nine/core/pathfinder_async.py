"""
Asynchronous pathfinding system for niNE.

Offloads pathfinding calculations to worker threads to prevent
blocking the main server tick. Essential for scaling to 300+ NPCs.

Key Features:
- Thread pool with configurable worker count
- Priority queue (combat > pursuit > patrol)
- Request deduplication (stale requests discarded)
- Non-blocking result polling

Usage:
    # Create async pathfinder
    async_pf = AsyncPathfinder(pathfinder, num_workers=2)
    async_pf.start()

    # Request a path
    request_id = async_pf.request_path(
        entity_id="npc_123",
        start=Vec3(0, 0, 0),
        goal=Vec3(10, 5, 0),
        priority=PathPriority.COMBAT
    )

    # In game loop, poll for results
    for result in async_pf.poll_results():
        if result.found:
            npc.set_path(result.path)

    # Shutdown
    async_pf.stop()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from queue import PriorityQueue, Queue, Empty
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from panda3d.core import Vec3
import logging

if TYPE_CHECKING:
    from nine.core.pathfinder import GridPathfinder

logger = logging.getLogger(__name__)


class PathPriority(IntEnum):
    """
    Priority levels for path requests.
    Lower values = higher priority.
    """
    COMBAT = 0       # NPC in combat, needs path NOW
    PURSUIT = 1      # NPC pursuing target
    FLEE = 2         # NPC fleeing
    PATROL = 3       # Routine patrol movement
    WANDER = 4       # Random wandering
    BACKGROUND = 5   # Low priority background recalc


@dataclass(order=True)
class PathRequest:
    """
    A pathfinding request in the queue.

    Note: order=True with priority first means lower priority values
    are processed first (higher priority).
    """
    priority: int
    request_id: int = field(compare=False)
    entity_id: str = field(compare=False)
    start: Tuple[float, float, float] = field(compare=False)
    goal: Tuple[float, float, float] = field(compare=False)
    timestamp: float = field(compare=False)
    max_iterations: int = field(default=5000, compare=False)


@dataclass
class PathResult:
    """
    Result of a pathfinding request.

    Attributes:
        request_id: Matches the request ID
        entity_id: Entity that requested the path
        path: List of Vec3 waypoints (empty if not found)
        found: Whether a path was found
        cost: Path cost if found
        compute_time: Time spent computing (seconds)
    """
    request_id: int
    entity_id: str
    path: List[Vec3]
    found: bool
    cost: float = 0.0
    compute_time: float = 0.0


class AsyncPathfinder:
    """
    Threaded pathfinding manager.

    Uses a pool of worker threads to compute paths in parallel.
    Requests are prioritized and results are polled from the main thread.
    """

    # Default limits
    DEFAULT_WORKERS = 2
    MAX_REQUESTS_PER_TICK = 10      # Max new requests accepted per tick
    REQUEST_TIMEOUT = 5.0           # Discard requests older than this (seconds)
    MAX_QUEUE_SIZE = 100            # Max pending requests

    def __init__(
        self,
        pathfinder: 'GridPathfinder',
        num_workers: int = DEFAULT_WORKERS
    ):
        """
        Initialize async pathfinder.

        Args:
            pathfinder: The synchronous pathfinder to use for calculations
            num_workers: Number of worker threads (2-4 recommended)
        """
        self.pathfinder = pathfinder
        self.num_workers = num_workers

        # Request and result queues
        self._request_queue: PriorityQueue[PathRequest] = PriorityQueue()
        self._result_queue: Queue[PathResult] = Queue()

        # Worker threads
        self._workers: List[threading.Thread] = []
        self._running = False
        self._shutdown_event = threading.Event()

        # Request tracking
        self._request_id_counter = 0
        self._request_lock = threading.Lock()

        # Entity tracking (to detect stale requests)
        self._entity_latest_request: Dict[str, int] = {}

        # Statistics
        self._stats = {
            "requests_total": 0,
            "requests_completed": 0,
            "requests_dropped": 0,
            "avg_compute_time": 0.0,
        }

        logger.info(f"AsyncPathfinder initialized with {num_workers} workers")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def start(self) -> None:
        """
        Start worker threads.

        Must be called before requesting paths.
        """
        if self._running:
            logger.warning("AsyncPathfinder already running")
            return

        self._running = True
        self._shutdown_event.clear()

        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"PathWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)

        logger.info(f"AsyncPathfinder started with {self.num_workers} workers")

    def stop(self, timeout: float = 2.0) -> None:
        """
        Stop worker threads gracefully.

        Args:
            timeout: Max seconds to wait for workers to finish
        """
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=timeout / self.num_workers)

        self._workers.clear()
        logger.info("AsyncPathfinder stopped")

    @property
    def is_running(self) -> bool:
        """Check if pathfinder is running."""
        return self._running

    # =========================================================================
    # Request Handling
    # =========================================================================

    def request_path(
        self,
        entity_id: str,
        start: Vec3,
        goal: Vec3,
        priority: PathPriority = PathPriority.PATROL,
        max_iterations: int = 5000
    ) -> int:
        """
        Queue a path request.

        If the entity already has a pending request, the new request
        replaces it (the old result will be ignored).

        Args:
            entity_id: Entity requesting the path
            start: Start position
            goal: Goal position
            priority: Request priority (lower = higher priority)
            max_iterations: Max A* iterations

        Returns:
            Request ID (used to match results)

        Raises:
            RuntimeError: If pathfinder not started
        """
        if not self._running:
            raise RuntimeError("AsyncPathfinder not started")

        # Check queue size limit
        if self._request_queue.qsize() >= self.MAX_QUEUE_SIZE:
            logger.warning("Path request queue full, dropping request")
            self._stats["requests_dropped"] += 1
            return -1

        with self._request_lock:
            self._request_id_counter += 1
            request_id = self._request_id_counter

            # Track latest request per entity (for staleness detection)
            self._entity_latest_request[entity_id] = request_id

        request = PathRequest(
            priority=priority,
            request_id=request_id,
            entity_id=entity_id,
            start=(start.x, start.y, start.z),
            goal=(goal.x, goal.y, goal.z),
            timestamp=time.time(),
            max_iterations=max_iterations
        )

        self._request_queue.put(request)
        self._stats["requests_total"] += 1

        return request_id

    def cancel_request(self, entity_id: str) -> None:
        """
        Cancel pending request for an entity.

        The request won't be removed from queue (too expensive),
        but its result will be ignored when processed.

        Args:
            entity_id: Entity whose request to cancel
        """
        with self._request_lock:
            self._entity_latest_request.pop(entity_id, None)

    def poll_results(self, max_results: int = 50) -> List[PathResult]:
        """
        Get completed path results (non-blocking).

        Should be called every tick from the main thread.

        Args:
            max_results: Maximum results to return per call

        Returns:
            List of PathResult objects
        """
        results = []

        for _ in range(max_results):
            try:
                result = self._result_queue.get_nowait()

                # Check if result is still relevant
                with self._request_lock:
                    latest_id = self._entity_latest_request.get(result.entity_id, -1)

                if result.request_id >= latest_id:
                    results.append(result)
                else:
                    # Stale result, entity has a newer request
                    pass

            except Empty:
                break

        return results

    def poll_result_for_entity(self, entity_id: str) -> Optional[PathResult]:
        """
        Poll for a specific entity's result.

        Useful when an entity needs to wait for its path.

        Args:
            entity_id: Entity to get result for

        Returns:
            PathResult if available, None otherwise
        """
        # This is less efficient, prefer poll_results() in bulk
        results = self.poll_results(max_results=100)
        for result in results:
            if result.entity_id == entity_id:
                return result
        return None

    # =========================================================================
    # Worker Thread
    # =========================================================================

    def _worker_loop(self) -> None:
        """
        Worker thread main loop.

        Processes path requests from the queue until shutdown.
        """
        logger.debug(f"Path worker {threading.current_thread().name} started")

        while self._running:
            try:
                # Wait for request with timeout (allows shutdown check)
                request = self._request_queue.get(timeout=0.1)
            except Empty:
                continue

            # Check if we should stop
            if self._shutdown_event.is_set():
                break

            # Process the request
            result = self._process_request(request)

            # Put result in queue if not stale
            with self._request_lock:
                latest_id = self._entity_latest_request.get(request.entity_id, -1)

            if request.request_id >= latest_id:
                self._result_queue.put(result)
                self._stats["requests_completed"] += 1

        logger.debug(f"Path worker {threading.current_thread().name} stopped")

    def _process_request(self, request: PathRequest) -> PathResult:
        """
        Process a single path request.

        Args:
            request: The request to process

        Returns:
            PathResult with the computed path
        """
        start_time = time.time()

        # Check if request is too old
        age = start_time - request.timestamp
        if age > self.REQUEST_TIMEOUT:
            return PathResult(
                request_id=request.request_id,
                entity_id=request.entity_id,
                path=[],
                found=False,
                compute_time=0.0
            )

        # Compute the path
        try:
            path_result = self.pathfinder.find_path(
                start=request.start,
                end=request.goal,
                max_iterations=request.max_iterations
            )

            compute_time = time.time() - start_time

            # Update average compute time (exponential moving average)
            self._stats["avg_compute_time"] = (
                0.9 * self._stats["avg_compute_time"] + 0.1 * compute_time
            )

            return PathResult(
                request_id=request.request_id,
                entity_id=request.entity_id,
                path=path_result.path if path_result.found else [],
                found=path_result.found,
                cost=path_result.cost,
                compute_time=compute_time
            )

        except Exception as e:
            logger.error(f"Pathfinding error for {request.entity_id}: {e}")
            return PathResult(
                request_id=request.request_id,
                entity_id=request.entity_id,
                path=[],
                found=False,
                compute_time=time.time() - start_time
            )

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict:
        """
        Get pathfinding statistics.

        Returns:
            Dict with stats (requests, completions, avg time, etc.)
        """
        return {
            **self._stats,
            "queue_size": self._request_queue.qsize(),
            "result_queue_size": self._result_queue.qsize(),
            "workers": self.num_workers,
            "running": self._running,
        }

    def get_queue_size(self) -> int:
        """Get number of pending requests."""
        return self._request_queue.qsize()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "requests_total": 0,
            "requests_completed": 0,
            "requests_dropped": 0,
            "avg_compute_time": 0.0,
        }


# =============================================================================
# Request Throttler (for rate limiting)
# =============================================================================

class PathRequestThrottler:
    """
    Rate limiter for path requests.

    Prevents overwhelming the async pathfinder with too many requests.
    Uses a token bucket algorithm with per-entity and global limits.
    """

    def __init__(
        self,
        requests_per_second: float = 20.0,
        per_entity_cooldown: float = 0.5
    ):
        """
        Initialize throttler.

        Args:
            requests_per_second: Global rate limit
            per_entity_cooldown: Min seconds between requests per entity
        """
        self.requests_per_second = requests_per_second
        self.per_entity_cooldown = per_entity_cooldown

        self._tokens = requests_per_second
        self._last_refill = time.time()
        self._entity_last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def try_acquire(self, entity_id: str) -> bool:
        """
        Try to acquire permission to make a request.

        Args:
            entity_id: Entity requesting

        Returns:
            True if request allowed, False if throttled
        """
        current_time = time.time()

        with self._lock:
            # Refill tokens
            elapsed = current_time - self._last_refill
            self._tokens = min(
                self.requests_per_second,
                self._tokens + elapsed * self.requests_per_second
            )
            self._last_refill = current_time

            # Check global limit
            if self._tokens < 1.0:
                return False

            # Check per-entity cooldown
            last_request = self._entity_last_request.get(entity_id, 0.0)
            if current_time - last_request < self.per_entity_cooldown:
                return False

            # Acquire
            self._tokens -= 1.0
            self._entity_last_request[entity_id] = current_time
            return True

    def clear_entity(self, entity_id: str) -> None:
        """Remove entity from tracking (on despawn)."""
        with self._lock:
            self._entity_last_request.pop(entity_id, None)

    def clear_all(self) -> None:
        """Reset all tracking."""
        with self._lock:
            self._entity_last_request.clear()
            self._tokens = self.requests_per_second


# =============================================================================
# Path Cache (optional, for frequently requested paths)
# =============================================================================

@dataclass
class CachedPath:
    """A cached path result with expiry time."""
    path: List[Vec3]
    found: bool
    cost: float
    timestamp: float
    hits: int = 0


class PathCache:
    """
    Simple LRU cache for frequently requested paths.

    Useful for static NPCs that patrol the same routes.
    """

    def __init__(self, max_size: int = 100, ttl: float = 60.0):
        """
        Initialize path cache.

        Args:
            max_size: Maximum cached paths
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[Tuple, CachedPath] = {}
        self._lock = threading.Lock()

    def _make_key(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        precision: float = 1.0
    ) -> Tuple:
        """Create cache key with position rounding."""
        def round_pos(pos):
            return (
                round(pos[0] / precision) * precision,
                round(pos[1] / precision) * precision,
                round(pos[2] / precision) * precision
            )
        return (round_pos(start), round_pos(goal))

    def get(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float]
    ) -> Optional[CachedPath]:
        """
        Get cached path if available.

        Args:
            start, goal: Path endpoints

        Returns:
            CachedPath if hit and not expired, None otherwise
        """
        key = self._make_key(start, goal)
        current_time = time.time()

        with self._lock:
            cached = self._cache.get(key)
            if cached and (current_time - cached.timestamp) < self.ttl:
                cached.hits += 1
                return cached
            elif cached:
                # Expired
                del self._cache[key]

        return None

    def put(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        path: List[Vec3],
        found: bool,
        cost: float = 0.0
    ) -> None:
        """
        Store path in cache.

        Args:
            start, goal: Path endpoints
            path: The computed path
            found: Whether path was found
            cost: Path cost
        """
        key = self._make_key(start, goal)

        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].timestamp
                )
                del self._cache[oldest_key]

            self._cache[key] = CachedPath(
                path=path,
                found=found,
                cost=cost,
                timestamp=time.time()
            )

    def clear(self) -> None:
        """Clear all cached paths."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            total_hits = sum(c.hits for c in self._cache.values())
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
                "ttl": self.ttl
            }
