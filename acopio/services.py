"""Reglas de negocio del acopio, en un solo lugar y dentro de transacciones."""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Max, Min, Sum
from django.utils import timezone
from precios.models import Campania, PrecioReferencia
from .models import DIAS_PAGO, Anticipo, Comprobante

DOS = Decimal("0.01")


class ReglaDeNegocio(Exception):
    """Un dato no cumple una regla de negocio: se muestra el mensaje al usuario."""


def redondear(valor):
    return Decimal(valor).quantize(DOS, rounding=ROUND_HALF_UP)


def calcular(kilos_brutos, tara, precio_kg, fecha_entrega):
    """Kilos netos, importe y fecha de pago (reglas 1 y 2)."""
    netos = redondear(kilos_brutos - tara)
    importe = redondear(netos * precio_kg)
    fecha_pago = timezone.localtime(fecha_entrega).date() + timedelta(days=DIAS_PAGO)
    return netos, importe, fecha_pago


@transaction.atomic
def registrar_comprobante(*, usuario, productor, producto, procedencia, kilos_brutos, tara, humedad,
                          fecha_entrega=None, carga_diferida=False, numero_papel=""):
    """Registra un comprobante con número único y permanente (HU10 y HU11)."""
    campania = Campania.objects.select_for_update().filter(vigente=True).first()
    if campania is None:
        raise ReglaDeNegocio("No hay una campaña vigente. Gerencia tiene que fijarla.")
    if not productor.activo:
        raise ReglaDeNegocio("El productor está inactivo.")
    if tara >= kilos_brutos:
        raise ReglaDeNegocio("La tara tiene que ser menor que los kilos brutos.")
    precio = PrecioReferencia.objects.filter(campania=campania, producto=producto).first()
    if precio is None:
        raise ReglaDeNegocio(f"No hay precio de referencia de {producto.nombre} para la {campania}. Lo fija Gerencia.")
    ahora = timezone.now()
    if carga_diferida:
        numero_papel = (numero_papel or "").strip()
        if not numero_papel:
            raise ReglaDeNegocio("En la carga diferida hay que indicar el número del comprobante en papel.")
        if fecha_entrega is None or fecha_entrega > ahora:
            raise ReglaDeNegocio("La fecha de la entrega no puede ser futura.")
        if Comprobante.objects.filter(campania=campania, numero_papel=numero_papel).exists():
            raise ReglaDeNegocio(f"El comprobante en papel {numero_papel} ya fue cargado.")
    else:
        fecha_entrega, numero_papel = ahora, ""
    # El candado sobre la campaña evita que dos cargas simultáneas tomen el mismo número
    ultimo = Comprobante.objects.filter(campania=campania).aggregate(m=Max("correlativo"))["m"] or 0
    correlativo = ultimo + 1
    netos, importe, fecha_pago = calcular(kilos_brutos, tara, precio.precio_kg, fecha_entrega)
    return Comprobante.objects.create(
        numero=f"{campania.anio}-{correlativo:05d}", campania=campania, correlativo=correlativo,
        productor=productor, procedencia=procedencia.strip(), producto=producto,
        precio_referencia=precio, precio_kg=precio.precio_kg,
        kilos_brutos=kilos_brutos, tara=tara, kilos_netos=netos, humedad=humedad, importe=importe,
        fecha_entrega=fecha_entrega, fecha_pago=fecha_pago,
        carga_diferida=carga_diferida, numero_papel=numero_papel, registrado_por=usuario,
    )


@transaction.atomic
def anular_comprobante(*, comprobante_id, motivo, usuario):
    """Anula con motivo, sin borrar: el número queda usado (HU12, regla 4)."""
    motivo = (motivo or "").strip()
    if len(motivo) < 5:
        raise ReglaDeNegocio("Escribí el motivo de la anulación (al menos 5 caracteres).")
    comprobante = Comprobante.objects.select_for_update().get(pk=comprobante_id)
    if comprobante.estado == Comprobante.Estado.ANULADO:
        raise ReglaDeNegocio("El comprobante ya estaba anulado.")
    comprobante.estado = Comprobante.Estado.ANULADO
    comprobante.motivo_anulacion = motivo
    comprobante.anulado_por = usuario
    comprobante.fecha_anulacion = timezone.now()
    comprobante.save(update_fields=["estado", "motivo_anulacion", "anulado_por", "fecha_anulacion"])
    return comprobante


def anticipo_repetido(productor, fecha, importe):
    """Aviso de posible duplicado: mismo productor, fecha e importe (HU13)."""
    return Anticipo.objects.filter(productor=productor, fecha=fecha, importe=importe).exists()


def cuenta_productor(productor, campania):
    """Cuenta del productor en la campaña: comprobantes, anticipos y saldo (HU14, regla 2)."""
    comprobantes = Comprobante.objects.filter(productor=productor, campania=campania, estado="registrado").select_related("producto")
    anticipos = Anticipo.objects.filter(productor=productor, campania=campania)
    total_kilos = comprobantes.aggregate(s=Sum("kilos_netos"))["s"] or Decimal("0")
    total_importe = comprobantes.aggregate(s=Sum("importe"))["s"] or Decimal("0")
    total_anticipos = anticipos.aggregate(s=Sum("importe"))["s"] or Decimal("0")
    hoy = timezone.localdate()
    proximo = comprobantes.filter(fecha_pago__gte=hoy).aggregate(m=Min("fecha_pago"))["m"]
    return {
        "comprobantes": comprobantes, "anticipos": anticipos,
        "total_kilos": total_kilos, "total_importe": total_importe, "total_anticipos": total_anticipos,
        "saldo": total_importe - total_anticipos, "proximo_pago": proximo,
    }


def saldos_pendientes(campania):
    """Productores con saldo mayor a cero, ordenados por el próximo vencimiento (HU16)."""
    from productores.models import Productor
    filas = []
    for productor in Productor.objects.filter(comprobantes__campania=campania).distinct():
        c = cuenta_productor(productor, campania)
        if c["saldo"] > 0:
            filas.append({"productor": productor, **c})
    lejos = timezone.localdate() + timedelta(days=3650)
    return sorted(filas, key=lambda f: (f["proximo_pago"] or lejos, str(f["productor"])))
