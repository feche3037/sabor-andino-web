"""Padrón de productores y productos con lote (Epic E2, HU05–HU08 y HU17).

Coincide con el DER: PRODUCTOR, PRODUCTO y PRODUCTOR_PRODUCTO (relación N:M).
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse

solo_numeros = RegexValidator(r"^\d{7,11}$", "Ingresá solo números: 7 u 8 para DNI, 11 para CUIT.")


class Producto(models.Model):
    nombre = models.CharField(max_length=80)
    lote = models.CharField(max_length=30, blank=True, help_text="Por ejemplo, L-2026-001.")
    presentacion = models.CharField("presentación", max_length=80, blank=True)
    activo = models.BooleanField(default=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(Lower("nombre"), name="producto_nombre_unico"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.lote})" if self.lote else self.nombre

    def get_absolute_url(self):
        return reverse("productores:producto_detalle", args=[self.pk])


class Productor(models.Model):
    nombre = models.CharField(max_length=60)
    apellido = models.CharField(max_length=60)
    dni_cuit = models.CharField("DNI o CUIT", max_length=11, unique=True, validators=[solo_numeros])
    localidad = models.CharField(max_length=60)
    direccion = models.CharField("dirección", max_length=120, blank=True)
    celular = models.CharField(max_length=20, blank=True)
    # Los productores no se borran: se desactivan para conservar su historial (HU08)
    activo = models.BooleanField(default=True)
    productos = models.ManyToManyField(Producto, through="ProductorProducto", related_name="productores", blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="productores_creados")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="productores_actualizados")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name_plural = "productores"

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def get_absolute_url(self):
        return reverse("productores:detalle", args=[self.pk])


class ProductorProducto(models.Model):
    """Qué productos entrega cada productor (tabla intermedia del DER)."""

    productor = models.ForeignKey(Productor, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    vinculado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["productor", "producto"], name="productor_producto_unico"),
        ]
