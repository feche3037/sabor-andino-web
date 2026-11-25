from django.contrib import admin
from .models import Campania, PrecioReferencia

admin.site.register(Campania)


@admin.register(PrecioReferencia)
class PrecioAdmin(admin.ModelAdmin):
    list_display = ("producto", "campania", "precio_kg", "fijado_por", "actualizado")
    list_filter = ("campania",)
