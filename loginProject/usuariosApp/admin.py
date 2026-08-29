from django.contrib import admin

# Register your models here.

from .models import Producto,  Comentario

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'vendedor', 'destacado_hasta')  # Campos a mostrar en la lista
    search_fields = ('nombre', 'descripcion')  # Campos que serán buscables
    list_filter = ('categoria', 'vendedor')  # Filtros disponibles en la barra lateral
    list_editable = ('categoria',)  # Campos que se pueden editar directamente desde la lista

class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'usuario', 'valoracion', 'fecha_creacion')  # Campos a mostrar en la lista
    search_fields = ('producto__nombre', 'usuario__username')  # Campos que serán buscables

# Registra los modelos en el admin
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Comentario, ComentarioAdmin)
