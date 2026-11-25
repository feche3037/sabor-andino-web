"""Comprobantes de acopio y anticipos (Epics E4, E5 y E6).

Coincide con el DER: COMPROBANTE_ACOPIO y ANTICIPO.
Nada se borra: los comprobantes se anulan con motivo (regla 4) y los anticipos quedan registrados.
"""

from decimal import Decimal
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

DIAS_PAGO = 30  # regla 2: se paga a los 30 días corridos del ingreso


class Comprobante(models.Model):
    class Estado(models.TextChoices):
        REGISTRADO = "registrado", "Registrado"
        ANULADO = "anulado", "Anulado"

    # Número único y permanente: año de campaña + correlativo (ej. 2026-00045)
    numero = models.CharField("número", max_length=20, unique=True, editable=False)
    campania = models.ForeignKey("precios.Campania", on_delete=models.PROTECT, related_name="comprobantes", verbose_name="campaña")
    correlativo = models.PositiveIntegerField(editable=False)
    productor = models.ForeignKey("productores.Productor", on_delete=models.PROTECT, related_name="comprobantes")
    procedencia = models.CharField(max_length=80)
    producto = models.ForeignKey("productores.Producto", on_delete=models.PROTECT, related_name="comprobantes")
    precio_referencia = models.ForeignKey("precios.PrecioReferencia", on_delete=models.PROTECT, related_name="comprobantes")
    precio_kg = models.DecimalField("precio por kilo", max_digits=12, decimal_places=2)
    kilos_brutos = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    tara = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    kilos_netos = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    humedad = models.DecimalField("humedad (%)", max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    importe = models.DecimalField(max_digits=14, decimal_places=2, editable=False)
    fecha_entrega = models.DateTimeField("fecha y hora de la entrega")
    fecha_pago = models.DateField(editable=False)
    # Carga diferida (HU11): el comprobante se hizo en papel en Cachi y se carga después
    carga_diferida = models.BooleanField(default=False)
    numero_papel = models.CharField("número del comprobante en papel", max_length=20, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.REGISTRADO)
    motivo_anulacion = models.TextField(blank=True)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="comprobantes_anulados")
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comprobantes_registrados")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-campania__anio", "-correlativo"]
        constraints = [
            models.UniqueConstraint(fields=["campania", "correlativo"], name="correlativo_unico_por_campania"),
            models.UniqueConstraint(fields=["campania", "numero_papel"], condition=~models.Q(numero_papel=""), name="papel_unico_por_campania"),
            models.CheckConstraint(condition=models.Q(tara__lt=models.F("kilos_brutos")), name="tara_menor_que_brutos"),
            models.CheckConstraint(condition=models.Q(humedad__gte=0, humedad__lte=100), name="humedad_entre_0_y_100"),
            models.CheckConstraint(condition=models.Q(estado="registrado") | ~models.Q(motivo_anulacion=""), name="anulado_con_motivo"),
            models.CheckConstraint(condition=models.Q(carga_diferida=False) | ~models.Q(numero_papel=""), name="diferida_con_numero_papel"),
        ]

    def __str__(self):
        return f"Comprobante {self.numero}"

    def get_absolute_url(self):
        return reverse("acopio:detalle", args=[self.pk])


class Anticipo(models.Model):
    campania = models.ForeignKey("precios.Campania", on_delete=models.PROTECT, related_name="anticipos", verbose_name="campaña")
    productor = models.ForeignKey("productores.Productor", on_delete=models.PROTECT, related_name="anticipos")
    fecha = models.DateField()
    importe = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    autorizado_por = models.CharField(max_length=80)
    observacion = models.CharField("observación", max_length=200, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="anticipos_registrados")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(importe__gt=0), name="anticipo_importe_positivo"),
        ]

    def __str__(self):
        return f"Anticipo {self.productor} {self.fecha:%d/%m/%Y} $ {self.importe}"
