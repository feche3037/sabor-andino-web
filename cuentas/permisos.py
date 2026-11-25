"""Matriz de permisos de Sabor Andino (AO2, punto 2.4).

Los permisos se controlan en el servidor, en cada vista: ocultar un botón no alcanza.
El superusuario (administrador del sistema) puede todo.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

GERENCIA = "gerencia"
ADMINISTRACION = "administracion"
COMPRAS = "compras"
ACOPIADOR = "acopiador"

# Qué roles pueden hacer cada acción
GESTIONAR_USUARIOS = (ADMINISTRACION,)
EDITAR_PRODUCTORES = (COMPRAS,)
EDITAR_PRODUCTOS = (COMPRAS, GERENCIA)
FIJAR_PRECIOS = (GERENCIA,)
REGISTRAR_ACOPIO = (ACOPIADOR, COMPRAS)
ANULAR_COMPROBANTES = (COMPRAS,)
REGISTRAR_ANTICIPOS = (ACOPIADOR, COMPRAS)
VER_CUENTAS = (ADMINISTRACION, COMPRAS, GERENCIA)


def tiene_rol(user, roles):
    if not (user.is_authenticated and user.is_active):
        return False
    return user.is_superuser or user.rol in roles


def exigir_rol(user, roles):
    if not tiene_rol(user, roles):
        raise PermissionDenied


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vista solo para usuarios con alguno de los roles indicados."""

    roles = ()

    def test_func(self):
        return tiene_rol(self.request.user, self.roles)


def permisos(user):
    """Banderas para mostrar u ocultar menús y botones en las plantillas."""
    return {
        "usuarios": tiene_rol(user, GESTIONAR_USUARIOS),
        "editar_productores": tiene_rol(user, EDITAR_PRODUCTORES),
        "editar_productos": tiene_rol(user, EDITAR_PRODUCTOS),
        "fijar_precios": tiene_rol(user, FIJAR_PRECIOS),
        "registrar_acopio": tiene_rol(user, REGISTRAR_ACOPIO),
        "anular": tiene_rol(user, ANULAR_COMPROBANTES),
        "anticipos": tiene_rol(user, REGISTRAR_ANTICIPOS),
        "cuentas": tiene_rol(user, VER_CUENTAS),
    }
