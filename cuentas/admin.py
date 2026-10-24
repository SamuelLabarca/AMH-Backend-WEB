from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """El admin de usuarios de Django, adaptado a un usuario sin `username`."""

    ordering = ["-fecha_registro"]
    list_display = ["correo", "nombre", "documento", "is_active", "is_staff", "fecha_registro"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["correo", "nombre", "documento"]
    readonly_fields = ["fecha_registro", "last_login"]
    fieldsets = [
        (None, {"fields": ["correo", "password"]}),
        ("Datos", {"fields": ["nombre", "documento", "telefono"]}),
        ("Permisos", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Fechas", {"fields": ["fecha_registro", "last_login"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["correo", "nombre", "documento", "password1", "password2"]}),
    ]
