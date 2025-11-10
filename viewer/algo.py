from collections.abc import Iterator, MutableSet, Sequence
from copy import copy
from itertools import chain, pairwise, product
from types import NotImplementedType
from typing import TYPE_CHECKING, Any, Final, Generic, Optional, Self, TypeVar, overload

from django.db.models import Q

from .models import HandlingUnit, SimPlacement, Simulation
from .rotation import Rotation

if TYPE_CHECKING:
    from _typeshed import SupportsAllComparisons
else:
    SupportsAllComparisons = Any

N = TypeVar("N", bound=SupportsAllComparisons)
T = TypeVar("T")


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


class Interval(Generic[N]):
    __slots__ = ("_max", "_min")
    __match_args__ = ("min", "max")

    _min: N
    _max: N

    def __init__(self, low: N, high: N, /) -> None:
        if low == high:
            raise ValueError("Intervals of measure 0 is not allowed")
        self._min = min(low, high)
        self._max = max(low, high)

    def __and__(self, other: Interval[N], /) -> Optional[Interval[N]]:
        "Returns None if the intervals have no intersection."
        if not isinstance(other, Interval):
            return NotImplemented
        low: Final[N] = max(self.min, other.min)
        high: Final[N] = min(self.max, other.max)
        if low >= high:
            return None
        ret: Final[Interval[N]] = Interval(low, high)
        if ret == self:
            return self
        elif ret == other:
            return other
        else:
            return ret

    def __contains__(self, other: Any, /) -> bool:
        try:
            return self.min <= other < self.max
        except TypeError:
            return False

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
    def max(self) -> N:
        return self._max

    @property
    def min(self) -> N:
        return self._min

    def __or__(self, other: Interval, /) -> Optional[Interval[N]]:
        "Returns None if the intervals have an unconnected union."
        if not isinstance(other, Interval):
            return NotImplemented
        if self.min > other.max or other.min > self.max:
            return None
        ret: Final[Interval[N]] = Interval(
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


class Mosaic(Generic[N, T]):
    class RangeError(LookupError):
        "Location lookup within a Mosaic is out of range."

    __slots__ = ("_grid_contents", "_x_boundaries", "_y_boundaries")

    _grid_contents: list[list[T]]
    _x_boundaries: list[N]
    _y_boundaries: list[N]

    def __init__(self, item: T, /, x_range: Interval[N], y_range: Interval[N]) -> None:
        self._grid_contents = [[item]]
        self._x_boundaries = [x_range.min, x_range.max]
        self._y_boundaries = [y_range.min, y_range.max]

    @staticmethod
    @overload
    def _interval_index_helper(intervals: Sequence[Interval[N]], find: N) -> int:
        pass

    @staticmethod
    @overload
    def _interval_index_helper(
        intervals: Sequence[Interval[N]], find: Interval[N]
    ) -> slice[int, int, None]:
        pass

    @staticmethod
    def _interval_index_helper(
        intervals: Sequence[Interval[N]], find: N | Interval[N]
    ) -> int | slice[int, int, None]:
        if isinstance(find, Interval):
            return slice(
                Mosaic._interval_index_helper(intervals, find.min),
                Mosaic._interval_index_helper(intervals, find.max),
            )  # type:ignore[return-value]
        left: int = 0
        right: int = len(intervals)
        middle: int
        if find not in Interval(intervals[0].min, intervals[-1].max):
            raise Mosaic.RangeError("Find target out of range")
        while left != right:
            middle = (left + right) // 2
            if find in intervals[middle]:
                return middle
            elif find < intervals[middle].min:
                right = middle
            else:
                left = middle + 1
        raise Exception(
            "Search location is between intervals. These intervals are likely corrupted."
        )

    def __contains__(self, other: Any, /) -> bool:
        return any(other in row for row in self._grid_contents)

    def __copy__(self) -> Self:
        ret: Final[Self] = type(self)(
            self[self._x_boundaries[0], self._x_boundaries[0]],
            self.x_range,
            self.y_range,
        )
        ret._grid_contents = [copy(column) for column in self._grid_contents]
        ret._x_boundaries = copy(self._x_boundaries)
        ret._y_boundaries = copy(self._y_boundaries)
        return ret

    def fuse(self) -> None:
        "Merge identical & adjacent rows/columns to reduce memory usage."
        i: int = 0
        while i < len(self.x_intervals):
            if self._grid_contents[i] == self._grid_contents[i + 1]:
                del self._grid_contents[i + 1]
                del self._x_boundaries[i + 1]
            else:
                i += 1
        i = 0
        while i < len(self.y_intervals):
            if all(column[i] == column[i + 1] for column in self._grid_contents):
                for column in self._grid_contents:
                    del column[i + 1]
                del self._y_boundaries[i + 1]
            else:
                i += 1

    @overload
    def __getitem__(self, key: tuple[N, N], /) -> T:
        pass

    @overload
    def __getitem__(self, key: tuple[Interval[N], Interval[N]], /) -> Mosaic[N, T]:
        pass

    def __getitem__(
        self, key: tuple[N, N] | tuple[Interval[N], Interval[N]], /
    ) -> T | Mosaic[N, T]:
        "When called over a range, this returns a **copy**, not a **view**."
        if isinstance(key[0], Interval):
            if key[0] & self.x_range != key[0] or key[1] & self.y_range != key[1]:
                raise self.RangeError(
                    "Specified range extends beyond the edge of the Mosaic."
                )
            ret: Final[Mosaic[N, T]] = copy(self)
            ret.x_range, ret.y_range = key
            return ret
        else:
            return self._grid_contents[
                self._interval_index_helper(self.x_intervals, key[0])
            ][self._interval_index_helper(self.x_intervals, key[1])]

    __hash__ = None  # type:ignore[assignment]

    def __iter__(self) -> Iterator[T]:
        return chain.from_iterable(self._grid_contents)

    def __len__(self) -> int:
        return (len(self._x_boundaries) + 1) * (len(self._y_boundaries) + 1)

    def overlay(self, other: Mosaic[N, T], /) -> None:
        "Replace contents of this mosaic with the contents of other where they overlap. Raises a `RangeError` if `other` is not completely inside `self`."
        if (
            self.x_range | other.x_range != self.x_range
            or self.y_range | other.y_range != self.y_range
        ):
            raise self.RangeError("overlay Mosaic out of range")
        for x, y in product(other.x_intervals, other.y_intervals):
            self[x, y] = other[x.min, y.min]

    def __setitem__(self, key: tuple[Interval[N], Interval[N]], value: T, /) -> None:
        try:
            self.slice_x(key[0].min)
        except ValueError:
            pass
        try:
            self.slice_x(key[0].max)
        except ValueError:
            pass
        try:
            self.slice_y(key[1].min)
        except ValueError:
            pass
        try:
            self.slice_y(key[1].max)
        except ValueError:
            pass

        for x_index, y_index in product(
            self._interval_index_helper(self.x_intervals, key[0]).indices(
                len(self._x_boundaries) - 1
            ),
            self._interval_index_helper(self.y_intervals, key[1]).indices(
                len(self._y_boundaries) - 1
            ),
        ):
            self._grid_contents[x_index][y_index] = value

    def slice_x(self, x: N, /) -> Interval[N]:
        "Returns the interval that was divided. Raises a ValueError if the Mosaic is already divided at the specified x coordinate."
        interval_index: Final[int] = self._interval_index_helper(self.x_intervals, x)
        if self.x_intervals[interval_index].min == x:
            raise ValueError(f"This Mosaic is already divided at x={x}")
        sliced_interval: Final[Interval[N]] = self.x_intervals[interval_index]
        self._x_boundaries.insert(interval_index + 1, x)
        self._grid_contents.insert(
            interval_index, copy(self._grid_contents[interval_index])
        )
        return sliced_interval

    def slice_y(self, y: N, /) -> Interval[N]:
        "Returns the interval that was divided. Raises a ValueError if the Mosaic is already divided at the specified y coordinate."
        interval_index: Final[int] = self._interval_index_helper(self.y_intervals, y)
        if self.y_intervals[interval_index].min == y:
            raise ValueError(f"This Mosaic is already divided at y={y}")
        sliced_interval: Final[Interval[N]] = self.y_intervals[interval_index]
        self._y_boundaries.insert(interval_index + 1, y)
        for column in self._grid_contents:
            column.insert(interval_index, column[interval_index])
        return sliced_interval

    @property
    def x_intervals(self) -> Sequence[Interval[N]]:
        return tuple(Interval(low, high) for low, high in pairwise(self._x_boundaries))

    @property
    def x_range(self) -> Interval[N]:
        return Interval(self._x_boundaries[0], self._x_boundaries[-1])

    @x_range.setter
    def x_range(self, value: Interval[N], /) -> None:
        if value & self.x_range is None:
            self._x_boundaries[:] = (value.min, value.max)
            self._grid_contents[:] = (
                self._grid_contents[-1 if value.min >= self.x_range.max else 0],
            )
            return
        if value.min >= self.x_range.min:
            while value.min not in self.x_intervals[0]:
                del self._x_boundaries[0]
                del self._grid_contents[0]
        self._x_boundaries[0] = value.min
        if value.max <= self.x_range.max:
            while value.max not in self.x_intervals[-1]:
                del self._x_boundaries[-1]
                del self._grid_contents[-1]
        self._x_boundaries[-1] = value.max

    @property
    def y_intervals(self) -> Sequence[Interval[N]]:
        return tuple(Interval(low, high) for low, high in pairwise(self._y_boundaries))

    @property
    def y_range(self) -> Interval[N]:
        return Interval(self._y_boundaries[0], self._y_boundaries[-1])

    @y_range.setter
    def y_range(self, value: Interval[N], /) -> None:
        if value & self.y_range is None:
            self._y_boundaries[:] = (value.min, value.max)
            for column in self._grid_contents:
                column[:] = (column[-1 if value.min >= self.y_range.max else 0],)
            return
        if value.min >= self.y_range.min:
            while value.min not in self.y_intervals[0]:
                del self._y_boundaries[0]
                for column in self._grid_contents:
                    del column[0]
        self._y_boundaries[0] = value.min
        if value.max <= self.y_range.max:
            while value.max not in self.y_intervals[-1]:
                del self._y_boundaries[-1]
                for column in self._grid_contents:
                    del column[-1]
        self._y_boundaries[-1] = value.max


def compute_stop(sim: Simulation, stop: str, /, starting_x: float) -> float:
    heightmap: Final[Mosaic[float, float]] = Mosaic(
        0, Interval(starting_x, 53.0 * 12), Interval(-9.0 * 12, 0)
    )
    for hu in HandlingUnit.objects.filter(
        Q(temp_add=sim) | Q(temp_add__isnull=True), shipment=sim.shipment, stop=stop
    ).order_by("-weight"):
        placement, _ = SimPlacement.objects.get_or_create(
            hu=hu, sim=sim, defaults={"x": 0, "y": 0, "z": 0}
        )
        for x, z, rot in product(
            heightmap.x_intervals, heightmap.y_intervals, Rotation
        ):
            effective_size: tuple[float, float, float] = rot.apply(
                (hu.x_size, hu.y_size, hu.z_size)
            )
            submap: Mosaic[float, float] = heightmap[
                Interval(x.min, x.min + effective_size[0]),
                Interval(z.min, z.min + effective_size[2]),
            ]
            submap.fuse()
            if (
                len(submap) == 1
                and submap[x.min, z.min] + effective_size[1] <= 8.5 * 12
            ):
                placement.x = x.min
                placement.x = z.min
                placement.y = heightmap[x.min, z.min]
                placement.orientation = rot
                heightmap[
                    Interval(x.min, x.min + effective_size[0]),
                    Interval(z.min, z.min + effective_size[2]),
                ] = (
                    placement.y + effective_size[1]
                )
                break
        else:
            raise ValueError("Could not fit all items!")
        placement.save()
    return starting_x
