from django.db import models
from django.utils import timezone

class Customer(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    endereco = models.CharField(max_length=200)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['-created_at']


class UnidadeConsumidora(models.Model):
    TIPO_CHOICES = [
        ('Residencial', 'Residencial'),
        ('Comercial', 'Comercial'),
        ('Industrial', 'Industrial'),
        ('Rural', 'Rural'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='unidades_consumidoras')
    codigo = models.CharField(max_length=50)
    endereco = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='Residencial')
    data_vigencia_inicio = models.DateField(default=timezone.now)
    data_vigencia_fim = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_active(self):
        """UC é ativa se não tem data de fim ou se a data de fim é futura"""
        if self.data_vigencia_fim is None:
            return True
        return self.data_vigencia_fim > timezone.now().date()
    
    def __str__(self):
        status = "Ativa" if self.is_active else "Inativa"
        return f"{self.codigo} - {self.customer.nome} ({status})"
    
    class Meta:
        ordering = ['-created_at']
        # Garante que um código de UC só pode estar ativo uma vez por cliente
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'codigo'],
                condition=models.Q(data_vigencia_fim__isnull=True),
                name='unique_active_uc_per_customer'
            )
        ]