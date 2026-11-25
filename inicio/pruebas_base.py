"""Datos comunes para las pruebas de Sabor Andino (usuarios por rol, campaña, producto y precio)."""

from decimal import Decimal
from django.test import TestCase, override_settings
from cuentas.models import Usuario
from precios.models import Campania, PrecioReferencia
from productores.models import Producto, Productor

CLAVE = "Temporal-segura-298!"


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class BaseSaborAndino(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser("admin", "admin@example.test", CLAVE)
        cls.usuarios = {}
        for rol in ("gerencia", "administracion", "compras", "acopiador"):
            cls.usuarios[rol] = Usuario.objects.create_user(
                rol, f"{rol}@example.test", CLAVE, estado="aprobado", is_active=True, rol=rol,
                first_name=rol.title(),
            )
        cls.campania = Campania.objects.create(anio=2026, vigente=True)
        cls.pimenton = Producto.objects.create(nombre="Pimentón", lote="L-2026-001")
        cls.comino = Producto.objects.create(nombre="Comino", lote="L-2026-003")
        cls.precio = PrecioReferencia.objects.create(
            campania=cls.campania, producto=cls.pimenton, precio_kg=Decimal("2850.00"), fijado_por=cls.usuarios["gerencia"]
        )
        cls.productor = Productor.objects.create(
            nombre="Rosa", apellido="Guanuco", dni_cuit="27111222", localidad="Cachi",
            creado_por=cls.usuarios["compras"], actualizado_por=cls.usuarios["compras"],
        )

    def como(self, rol):
        user = self.admin if rol == "admin" else self.usuarios[rol]
        self.client.force_login(user)
        return user
