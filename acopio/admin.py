from django.contrib import admin
from .models import Anticipo, Comprobante


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    list_display = ("numero", "productor", "producto", "kilos_netos", "importe", "estado", "carga_diferida")
    list_filter = ("estado", "campania", "carga_diferida")
    search_fields = ("numero", "numero_papel", "productor__apellido")

    # Los comprobantes solo se registran y anulan desde el sistema: el número es permanente
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Anticipo)
class AnticipoAdmin(admin.ModelAdmin):
    list_display = ("productor", "fecha", "importe", "autorizado_por", "registrado_por")
    list_filter = ("campania",)

    def has_delete_permission(self, request, obj=None):
        return False
