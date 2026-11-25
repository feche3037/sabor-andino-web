"""Campañas y precios de referencia (Epic E3, HU09, regla 3).

Coincide con el DER: CAMPANIA y PRECIO_REFERENCIA.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db import models


class Campania(models.Model):
    anio = models.PositiveSmallIntegerField("año", unique=True, validators=[MinValueValidator(2020)])
    vigente = models.BooleanField(default=False)

    class Meta:
        ordering = ["-anio"]
        verbose_name = "campaña"
        constraints = [
            # Solo puede haber una campaña vigente
            models.UniqueConstraint(fields=["vigente"], condition=models.Q(vigente=True), name="una_sola_campania_vigente"),
        ]

    def __str__(self):
        return f"Campaña {self.anio}"

    @classmethod
    def actual(cls):
        return cls.objects.filter(vigente=True).first()


class PrecioReferencia(models.Model):
    campania = models.ForeignKey(Campania, on_delete=models.PROTECT, related_name="precios", verbose_name="campaña")
    producto = models.ForeignKey("productores.Producto", on_delete=models.PROTECT, related_name="precios")
    precio_kg = models.DecimalField("precio por kilo", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    fijado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["producto__nombre"]
        verbose_name = "precio de referencia"
        verbose_name_plural = "precios de referencia"
        constraints = [
            models.UniqueConstraint(fields=["campania", "producto"], name="un_precio_por_producto_y_campania"),
            models.CheckConstraint(condition=models.Q(precio_kg__gt=0), name="precio_kg_positivo"),
        ]

    def __str__(self):
        return f"{self.producto.nombre} · {self.campania}: $ {self.precio_kg}/kg"
