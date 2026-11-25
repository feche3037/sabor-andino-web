"""Pruebas de roles y usuarios (HU01–HU04) agregadas por el grupo."""

from django.urls import reverse
from inicio.pruebas_base import BaseSaborAndino, CLAVE
from .models import Usuario


class RolesTests(BaseSaborAndino):
    def setUp(self):
        self.pendiente = Usuario.objects.create_user("nueva", "nueva@example.test", CLAVE)

    def test_administracion_aprueba_con_rol(self):
        self.como("administracion")
        self.client.post(reverse("cuentas:resolver", args=[self.pendiente.pk]), {"accion": "aprobar", "rol": "acopiador"})
        self.pendiente.refresh_from_db()
        self.assertTrue(self.pendiente.is_active)
        self.assertEqual(self.pendiente.rol, "acopiador")

    def test_no_se_aprueba_sin_rol(self):
        self.como("administracion")
        self.client.post(reverse("cuentas:resolver", args=[self.pendiente.pk]), {"accion": "aprobar"})
        self.pendiente.refresh_from_db()
        self.assertFalse(self.pendiente.is_active)
        self.assertEqual(self.pendiente.estado, "pendiente")

    def test_otros_roles_no_gestionan_usuarios(self):
        for rol in ("gerencia", "compras", "acopiador"):
            self.como(rol)
            self.assertEqual(self.client.get(reverse("cuentas:solicitudes")).status_code, 403)
            self.assertEqual(self.client.get(reverse("cuentas:usuarios")).status_code, 403)

    def test_cambiar_rol_y_desactivar(self):
        self.como("administracion")
        acopiador = self.usuarios["acopiador"]
        self.client.post(reverse("cuentas:modificar_usuario", args=[acopiador.pk]), {"rol": "compras", "activo": "no"})
        acopiador.refresh_from_db()
        self.assertEqual(acopiador.rol, "compras")
        self.assertFalse(acopiador.is_active)
        self.client.logout()
        self.client.post(reverse("cuentas:login"), {"username": "acopiador", "password": CLAVE})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_perfil_no_permite_cambiar_el_rol(self):
        user = self.como("acopiador")
        self.client.post(reverse("cuentas:perfil"), {
            "first_name": "Pedro", "last_name": "Cruz", "email": "pedro@example.test", "puesto": "Acopiador", "rol": "gerencia",
        })
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Pedro")
        self.assertEqual(user.rol, "acopiador")

    def test_menu_segun_rol(self):
        self.como("acopiador")
        html = self.client.get(reverse("inicio:home")).content.decode()
        self.assertNotIn(reverse("acopio:saldos"), html)
        self.assertNotIn(reverse("cuentas:solicitudes"), html)
        self.como("administracion")
        html = self.client.get(reverse("inicio:home")).content.decode()
        self.assertIn(reverse("cuentas:solicitudes"), html)
