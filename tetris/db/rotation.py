from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from enum import Enum, unique
from typing import Any, Final, Optional, TypeVar

from django.db.models import Field

T = TypeVar("T")


@unique
class Rotation(Enum):
    XYZ = "XYZ"
    XZY = "XZY"
    YXZ = "YXZ"
    YZX = "YZX"
    ZXY = "ZXY"
    ZYX = "ZYX"

    @property
    def _mapping(self) -> Mapping[int, int]:
        return {
            orig: new
            for orig, new in zip(
                range(3), (ord(char) - ord("X") for char in self.value), strict=True
            )
        }

    def apply(self, coords: tuple[T, T, T], /) -> tuple[T, T, T]:
        ret: Final[MutableMapping[int, T]] = {}
        for orig, new in self._mapping.items():
            ret[new] = coords[orig]
        return (ret[0], ret[1], ret[2])

    def __matmul__(self, other: Rotation, /) -> Rotation:
        if isinstance(other, Rotation):
            return Rotation(
                "".join("XYZ"[other._mapping[self._mapping[orig]]] for orig in range(3))
            )
        else:
            return NotImplemented


class RotationField(Field):
    description = "An orientation for a 3D object"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 3
        kwargs["choices"] = {member.value: member.value for member in Rotation}
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"], kwargs["choices"]
        return name, path, args, kwargs

    def from_db_value(
        self, value: Optional[str], expression: Any, connection: Any
    ) -> Optional[Rotation]:
        if value is None:
            return value
        return Rotation(value)

    def to_python(self, value: Optional[Rotation | str]) -> Optional[Rotation]:
        if value is None or isinstance(value, Rotation):
            return value
        return Rotation(value)

    def get_prep_value(self, value: Rotation) -> str:
        return value.value
