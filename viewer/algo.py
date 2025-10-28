from collections.abc import MutableSet
from types import NotImplementedType
from typing import Any, Final, Optional, Self, SupportsFloat

from django.db.models import Q

from db.models import HandlingUnit, SimPlacement, Simulation


def compute_layout(sim: Simulation, /) -> None:
    stops: MutableSet[str] = set()
    for hu in HandlingUnit.objects.filter(
        Q(temp_add=sim) | Q(temp_add__isnull=True),
        Q(simplacement__sim=sim, simplacement__temp_remove=False)
        | Q(simplacement__isnull=True),
        shipment=sim.shipment,
    ):
        stops.add(hu.stop)
    base_x: float = 0.0
    for stop in sorted(stops):
        base_x = compute_stop(sim, stop, base_x)


class Interval:
    __slots__ = ("_max", "_min")
    __match_args__ = ("min", "max")

    _min: Final[float]
    _max: Final[float]

    def __init__(self, low: float, high: float, /) -> None:
        self._min = min(low, high)
        self._max = max(low, high)

    def __and__(self, other: Interval, /) -> Optional[Interval]:
        "Returns None if the intervals have no intersection."
        if not isinstance(other, Interval):
            return NotImplemented
        low: Final[float] = max(self.min, other.min)
        high: Final[float] = min(self.max, other.max)
        if low >= high:
            return None
        ret: Final[Interval] = Interval(low, high)
        if ret == self:
            return self
        elif ret == other:
            return other
        else:
            return ret

    def __contains__(self, other: Any, /) -> bool:
        if not isinstance(other, SupportsFloat):
            return False
        return self.min <= float(other) < self.max

    def __copy__(self) -> Self:
        return self

    __deepcopy__ = __copy__

    def __eq__(self, other: Any, /) -> bool | NotImplementedType:
        if not isinstance(other, Interval):
            return NotImplemented
        return self.min == other.min and self.max == other.max

    def __hash__(self) -> int:
        return hash((self.min, self.max))

    @property
    def max(self) -> float:
        return self._max

    def measure(self) -> float:
        return self.max - self.min

    @property
    def min(self) -> float:
        return self._min

    def __or__(self, other: Interval, /) -> Optional[Interval]:
        "Returns None if the intervals have an unconnected union."
        if not isinstance(other, Interval):
            return NotImplemented
        if self.min > other.max or other.min > self.max:
            return None
        ret: Final[Interval] = Interval(
            min(self.min, other.min), max(self.max, other.max)
        )
        if ret == self:
            return self
        elif ret == other:
            return other
        else:
            return ret

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.min!r}, {self.max!r})"

    def __str__(self) -> str:
        return f"[{self.min}, {self.max})"


def compute_stop(sim: Simulation, stop: str, /, starting_x: float) -> float:
    for hu in HandlingUnit.objects.filter(
        Q(temp_add=sim) | Q(temp_add__isnull=True), shipment=sim.shipment, stop=stop
    ).order_by("-weight"):
        placement, _ = SimPlacement.objects.get_or_create(
            hu=hu, sim=sim, defaults={"x": 0, "y": 0, "z": 0}
        )
        if not placement.temp_remove:
            placement.x = starting_x
            placement.y = 0
            placement.z = 0
    return starting_x
