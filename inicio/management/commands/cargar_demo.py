from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from precios.models import Campania, PrecioReferencia
from productores.models import Producto, Productor, ProductorProducto


class Command(BaseCommand):
    help = (
        "Agrega datos ficticios de Sabor Andino (campaña, productos, precios y productores) "
        "sin modificar registros existentes. No crea cuentas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Nombre del administrador existente")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            usuario = get_user_model().objects.get(username=options["usuario"], is_superuser=True, is_active=True)
        except get_user_model().DoesNotExist:
            raise CommandError("Primero creá un administrador con createsuperuser.")
        campania, _ = Campania.objects.get_or_create(anio=2026)
        if not Campania.objects.filter(vigente=True).exists():
            campania.vigente = True
            campania.save(update_fields=["vigente"])
        productos = {}
        for nombre, lote, presentacion, precio in [
            ("Pimentón", "L-2026-001", "Vaina seca, bolsa de 25 kg", "2850.00"),
            ("Ají molido", "L-2026-002", "Vaina seca, bolsa de 25 kg", "3100.00"),
            ("Comino", "L-2026-003", "Semilla, bolsa de 20 kg", "4200.00"),
            ("Orégano", "L-2026-004", "Hoja seca, bolsa de 10 kg", "3900.00"),
        ]:
            producto = Producto.objects.filter(nombre__iexact=nombre).first() or Producto.objects.create(
                nombre=nombre, lote=lote, presentacion=presentacion
            )
            productos[nombre] = producto
            PrecioReferencia.objects.get_or_create(
                campania=campania, producto=producto, defaults={"precio_kg": Decimal(precio), "fijado_por": usuario}
            )
        for nombre, apellido, dni, localidad, entrega in [
            ("Rosa", "Guanuco (DEMO)", "90000001", "Cachi", ["Pimentón", "Comino"]),
            ("Julio", "Tolaba (DEMO)", "90000002", "Payogasta", ["Pimentón"]),
            ("Ana", "Mamaní (DEMO)", "90000003", "Seclantás", ["Ají molido", "Orégano"]),
        ]:
            productor = Productor.objects.filter(dni_cuit=dni).first()
            if not productor:
                productor = Productor.objects.create(
                    nombre=nombre, apellido=apellido, dni_cuit=dni, localidad=localidad,
                    creado_por=usuario, actualizado_por=usuario,
                )
            for p in entrega:
                ProductorProducto.objects.get_or_create(productor=productor, producto=productos[p])
        self.stdout.write(self.style.SUCCESS("Datos ficticios disponibles; los registros existentes se conservaron."))
