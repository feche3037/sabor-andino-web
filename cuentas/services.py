"""La decisión de acceso se registra junto con quien la tomó."""

from django.contrib.admin.models import LogEntry, CHANGE
from django.db import transaction
from .models import Usuario
from .permisos import tiene_rol, GESTIONAR_USUARIOS


def puede_gestionar(administrador):
    return tiene_rol(administrador, GESTIONAR_USUARIOS)


def _registrar(administrador, usuario, mensaje):
    LogEntry.objects.log_actions(
        user_id=administrador.pk,
        queryset=Usuario.objects.filter(pk=usuario.pk),
        action_flag=CHANGE,
        change_message=mensaje,
    )


@transaction.atomic
def resolver_solicitud(*, usuario_id, aprobar, administrador, rol=""):
    """Aprueba (con un rol) o rechaza una solicitud de acceso (HU02)."""
    if not puede_gestionar(administrador):
        raise PermissionError("Solo Administración puede resolver solicitudes.")
    if aprobar and rol not in Usuario.Rol.values:
        raise ValueError("Para aprobar una cuenta hay que asignarle un rol.")
    usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
    if usuario.estado != Usuario.Estado.PENDIENTE:
        return False
    usuario.estado = Usuario.Estado.APROBADO if aprobar else Usuario.Estado.RECHAZADO
    usuario.is_active = aprobar
    usuario.rol = rol if aprobar else ""
    usuario.save(update_fields=["estado", "is_active", "rol"])
    _registrar(
        administrador,
        usuario,
        f"Solicitud aprobada con rol {usuario.get_rol_display()}" if aprobar else "Solicitud rechazada",
    )
    return True


@transaction.atomic
def actualizar_acceso(*, usuario_id, rol, activo, administrador):
    """Cambia el rol o desactiva un usuario aprobado, sin borrarlo (HU03)."""
    if not puede_gestionar(administrador):
        raise PermissionError("Solo Administración puede modificar usuarios.")
    if rol not in Usuario.Rol.values:
        raise ValueError("Rol inválido.")
    usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
    if usuario.estado != Usuario.Estado.APROBADO or usuario.is_superuser:
        raise ValueError("Solo se modifican cuentas aprobadas que no sean del administrador del sistema.")
    if usuario.pk == administrador.pk and not activo:
        raise ValueError("No podés desactivar tu propia cuenta.")
    cambios = []
    if usuario.rol != rol:
        cambios.append(f"rol {usuario.get_rol_display()} → {Usuario.Rol(rol).label}")
    if usuario.is_active != activo:
        cambios.append("reactivado" if activo else "desactivado")
    if not cambios:
        return False
    usuario.rol = rol
    usuario.is_active = activo
    usuario.save(update_fields=["rol", "is_active"])
    _registrar(administrador, usuario, "Usuario " + ", ".join(cambios))
    return True
