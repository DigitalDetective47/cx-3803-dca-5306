from enum import Flag, unique
from typing import Any, Optional

from django.db.models import Field


@unique
class Restriction(Flag):
    THIS_SIDE_UP = 1
    NO_STACKING = 2


class RestrictionField(Field):
    description = "A set of loadig restrictions"

    def from_db_value(
        self, value: Optional[int], expression: Any, connection: Any
    ) -> Optional[Restriction]:
        if value is None:
            return Restriction(0)
        return Restriction(value)

    def to_python(self, value: Optional[Restriction | int]) -> Optional[Restriction]:
        if value is None:
            return Restriction(0)
        elif isinstance(value, Restriction):
            return value
        return Restriction(value)

    def get_prep_value(self, value: Optional[Restriction | int]) -> int:
        if value is None:
            return 0
        elif isinstance(value, int):
            return value
        return value.value

    def db_type(self, connection):
        return "smallint unsigned"
