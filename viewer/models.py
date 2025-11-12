from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    Model,
    PositiveBigIntegerField,
    UniqueConstraint,
)

from .rotation import Rotation, RotationField


class Shipment(Model):
    id = PositiveBigIntegerField(primary_key=True)
    name = CharField(max_length=64, blank=True)


class Simulation(Model):
    name = CharField(max_length=128, default="Unnamed Load")
    shipment = ForeignKey(Shipment, CASCADE)
    time = DateTimeField(auto_now_add=True)


class HandlingUnit(Model):
    id = CharField(max_length=9, primary_key=True)
    weight = FloatField()
    x_size = FloatField()
    y_size = FloatField()
    z_size = FloatField()
    shipment = ForeignKey(Shipment, CASCADE)
    stop = CharField(max_length=3)
    temp_add = ForeignKey(Simulation, CASCADE, null=True)


class SimPlacement(Model):
    hu = ForeignKey(HandlingUnit, CASCADE)
    x = FloatField()
    y = FloatField()
    z = FloatField()
    orientation = RotationField(default=Rotation.XYZ)
    sim = ForeignKey(Simulation, CASCADE)
    temp_remove = BooleanField(default=False)

    class Meta:
        constraints = (
            UniqueConstraint(fields=("hu", "sim"), name="shrodingers_placement"),
        )



class SavedConfiguration(Model):
    simulation = ForeignKey(Simulation, CASCADE)
    name = CharField(max_length=100, default="Untitled Configuration")
    created_at = DateTimeField(auto_now_add=True)


class SavedPlacement(Model):
    configuration = ForeignKey(SavedConfiguration, CASCADE, related_name="placements")
    handling_unit = ForeignKey(HandlingUnit, CASCADE)
    x = FloatField()
    y = FloatField()
    z = FloatField()
    orientation = CharField(max_length=10, default="XYZ")