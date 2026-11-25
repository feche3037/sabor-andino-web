"""Pruebas de productores y productos (HU05–HU08 y HU17)."""

from django.urls import reverse
from inicio.pruebas_base import BaseSaborAndino
from .models import Producto, Productor


class ProductoresTests(BaseSaborAndino):
    datos = {"nombre": "julio", "apellido": "tolaba", "dni_cuit": "20-30111222-5", "localidad": "Payogasta", "direccion": "", "celular": ""}

    def test_compras_registra_productor(self):
        self.como("compras")
        r = self.client.post(reverse("productores:crear"), self.datos)
        p = Productor.objects.get(dni_cuit="20301112225")
        self.assertRedirects(r, p.get_absolute_url())
        self.assertEqual((p.nombre, p.apellido), ("Julio", "Tolaba"))
        self.assertTrue(p.activo)

    def test_dni_repetido_o_con_letras(self):
        self.como("compras")
        r = self.client.post(reverse("productores:crear"), {**self.datos, "dni_cuit": "27111222"})
        self.assertContains(r, "Ya hay un productor registrado con ese DNI")
        r = self.client.post(reverse("productores:crear"), {**self.datos, "dni_cuit": "ABC12345"})
        self.assertContains(r, "Ingresá solo números")
        self.assertEqual(Productor.objects.count(), 1)

    def test_otros_roles_no_cargan_productores(self):
        for rol in ("acopiador", "gerencia", "administracion"):
            self.como(rol)
            self.assertEqual(self.client.post(reverse("productores:crear"), self.datos).status_code, 403)

    def test_busqueda_por_localidad(self):
        self.como("acopiador")
        self.assertContains(self.client.get(reverse("productores:lista"), {"q": "cachi"}), "Guanuco")
        self.assertNotContains(self.client.get(reverse("productores:lista"), {"q": "seclantas"}), "Guanuco")

    def test_editar_productor(self):
        self.como("compras")
        self.client.post(reverse("productores:editar", args=[self.productor.pk]), {**self.datos, "dni_cuit": "27111222", "celular": "3875550000"})
        self.productor.refresh_from_db()
        self.assertEqual(self.productor.celular, "3875550000")
        self.assertEqual(self.productor.actualizado_por, self.usuarios["compras"])

    def test_desactivar_sin_borrar(self):
        self.como("compras")
        self.client.post(reverse("productores:estado", args=[self.productor.pk]))
        self.productor.refresh_from_db()
        self.assertFalse(self.productor.activo)
        self.assertNotIn(self.productor, self.client.get(reverse("productores:lista")).context["object_list"])
        self.assertIn(self.productor, self.client.get(reverse("productores:lista"), {"estado": "inactivos"}).context["object_list"])
        self.assertEqual(self.client.get(reverse("productores:estado", args=[self.productor.pk])).status_code, 405)

    def test_agregar_y_quitar_productos_de_la_ficha(self):
        self.como("compras")
        self.client.post(reverse("productores:vincular", args=[self.productor.pk]), {"producto": self.pimenton.pk})
        self.assertIn(self.productor, self.pimenton.productores.all())
        self.assertContains(self.client.get(self.productor.get_absolute_url()), "L-2026-001")
        self.client.post(reverse("productores:quitar", args=[self.productor.pk, self.pimenton.pk]))
        self.assertNotIn(self.productor, self.pimenton.productores.all())
        self.assertTrue(Producto.objects.filter(pk=self.pimenton.pk).exists())

    def test_productos_con_lote(self):
        self.como("gerencia")
        self.client.post(reverse("productores:producto_crear"), {"nombre": "Orégano", "lote": "l-2026-004", "presentacion": "", "activo": "on"})
        self.assertEqual(Producto.objects.get(nombre="Orégano").lote, "L-2026-004")
        self.como("acopiador")
        self.assertEqual(self.client.get(reverse("productores:producto_crear")).status_code, 403)
