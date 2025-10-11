from django.db.models import (
    CASCADE,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    Model,
    PositiveBigIntegerField,
)

from .rotation import Rotation, RotationField


class Shipment(Model):
    id = PositiveBigIntegerField(primary_key=True)
    name = CharField(max_length=64, blank=True)


class HandlingUnit(Model):
    id = CharField(max_length=9, primary_key=True)
    weight = FloatField()
    x_size = FloatField()
    y_size = FloatField()
    z_size = FloatField()
    shipment = ForeignKey(Shipment, CASCADE)
    stop = CharField(max_length=3)


class Simulation(Model):
    time = DateTimeField()


class SimPlacement(Model):
    hu = ForeignKey(HandlingUnit, CASCADE)
    x = FloatField()
    y = FloatField()
    z = FloatField()
    orientation = RotationField(default=Rotation.XYZ)
    sim = ForeignKey(Simulation, CASCADE)
