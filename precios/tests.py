"""Pruebas de campañas y precios de referencia (HU09, regla 3)."""

from django.db import IntegrityError, transaction
from django.urls import reverse
from inicio.pruebas_base import BaseSaborAndino
from .models import Campania, PrecioReferencia


class PreciosTests(BaseSaborAndino):
    def test_gerencia_fija_y_cambia_precio(self):
        self.como("gerencia")
        self.client.post(reverse("precios:precios"), {"producto": self.comino.pk, "precio_kg": "4200"})
        self.client.post(reverse("precios:precios"), {"producto": self.comino.pk, "precio_kg": "4300"})
        precio = PrecioReferencia.objects.get(campania=self.campania, producto=self.comino)
        self.assertEqual(str(precio.precio_kg), "4300.00")

    def test_otros_roles_solo_consultan(self):
        for rol in ("compras", "acopiador", "administracion"):
            self.como(rol)
            self.assertContains(self.client.get(reverse("precios:precios")), "2850")
            self.assertEqual(self.client.post(reverse("precios:precios"), {"producto": self.comino.pk, "precio_kg": "1"}).status_code, 403)

    def test_precio_debe_ser_positivo(self):
        self.como("gerencia")
        self.client.post(reverse("precios:precios"), {"producto": self.comino.pk, "precio_kg": "0"})
        self.assertFalse(PrecioReferencia.objects.filter(producto=self.comino).exists())

    def test_una_sola_campania_vigente(self):
        self.como("gerencia")
        self.client.post(reverse("precios:crear_campania"), {"anio": 2027})
        nueva = Campania.objects.get(anio=2027)
        self.client.post(reverse("precios:vigente", args=[nueva.pk]))
        self.assertEqual(Campania.actual(), nueva)
        self.assertEqual(Campania.objects.filter(vigente=True).count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Campania.objects.filter(pk=self.campania.pk).update(vigente=True)
