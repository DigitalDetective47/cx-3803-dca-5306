from db.models import HandlingUnit, SimPlacement, Simulation


def compute_layout(sim: Simulation, /) -> None:
    for hu in HandlingUnit.objects.filter(
        shipment=sim.shipment, temp_add__in={None, sim}
    ):
        placement, _ = SimPlacement.objects.get_or_create(
            hu=hu, sim=sim, defaults={"x": 0, "y": 0, "z": 0}
        )
        if not placement.temp_remove:
            placement.x = 0
            placement.y = 0
            placement.z = 0
