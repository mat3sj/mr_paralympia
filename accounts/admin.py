from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ['-date_joined']
    list_display = ['email', 'first_name', 'last_name', 'birth_year', 'is_approved', 'date_joined']
    list_filter = ['is_approved', 'is_staff', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    actions = ['approve']
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Profile', {'fields': ['first_name', 'last_name', 'birth_year', 'hometown', 'job', 'hobbies', 'photo', 'language']}),
        ('Access', {'fields': ['is_approved', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
        ('Dates', {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {'classes': ['wide'], 'fields': ['email', 'password1', 'password2']}),
    ]

    @admin.action(description='Approve selected users')
    def approve(self, request, queryset):
        queryset.update(is_approved=True)
