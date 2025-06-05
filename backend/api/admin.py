from django.contrib import admin
from .models import Customer, UnidadeConsumidora

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'email', 'telefone', 'created_at']
    search_fields = ['nome', 'cpf', 'email']
    list_filter = ['created_at']
    ordering = ['-created_at']

@admin.register(UnidadeConsumidora)
class UnidadeConsumidoraAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'customer', 'endereco', 'tipo', 'data_vigencia_inicio', 'data_vigencia_fim', 'is_active']
    list_filter = ['tipo', 'data_vigencia_inicio', 'data_vigencia_fim']
    search_fields = ['codigo', 'customer__nome', 'endereco']
    raw_id_fields = ['customer']
    date_hierarchy = 'data_vigencia_inicio'
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Ativa'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('customer', 'codigo', 'endereco', 'tipo')
        }),
        ('Vigência', {
            'fields': ('data_vigencia_inicio', 'data_vigencia_fim'),
            'description': 'Deixe a data de fim em branco para UC ativa'
        }),
    )