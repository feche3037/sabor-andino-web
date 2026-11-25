from django.contrib import admin
from .models import Producto, Productor, ProductorProducto


class VinculoInline(admin.TabularInline):
    model = ProductorProducto
    extra = 0


@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "dni_cuit", "localidad", "activo")
    search_fields = ("apellido", "nombre", "dni_cuit", "localidad")
    list_filter = ("activo", "localidad")
    inlines = [VinculoInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "lote", "presentacion", "activo")
