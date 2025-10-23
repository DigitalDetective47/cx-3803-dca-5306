from collections.abc import MutableSet

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


def compute_stop(sim: Simulation, stop: str, /, starting_x: float) -> float:
    for hu in HandlingUnit.objects.filter(
        Q(temp_add=sim) | Q(temp_add__isnull=True), shipment=sim.shipment, stop=stop
    ):
        placement, _ = SimPlacement.objects.get_or_create(
            hu=hu, sim=sim, defaults={"x": 0, "y": 0, "z": 0}
        )
        if not placement.temp_remove:
            placement.x = starting_x
            placement.y = 0
            placement.z = 0
    return starting_x
