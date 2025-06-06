# backend/api/models.py
from django.db import models
from django.utils import timezone

class Customer(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    cpf_titular = models.CharField(max_length=14, blank=True, null=True, 
                                   verbose_name="CPF do Titular da UC")
    data_nascimento = models.DateField(blank=True, null=True)
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


class FaturaTask(models.Model):
    """Modelo para armazenar tarefas de download de faturas"""
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluída'),
        ('failed', 'Falhou'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='fatura_tasks')
    unidade_consumidora = models.ForeignKey(UnidadeConsumidora, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']


class FaturaLog(models.Model):
    """Log de buscas de faturas por CPF"""
    cpf_titular = models.CharField(max_length=14)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='fatura_logs')
    ucs_encontradas = models.JSONField(default=list)  # Lista de UCs encontradas
    faturas_encontradas = models.JSONField(default=dict)  # Dict com UC como chave e lista de faturas como valor
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class Fatura(models.Model):
    """Modelo para armazenar as faturas baixadas"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='faturas')
    unidade_consumidora = models.ForeignKey(UnidadeConsumidora, on_delete=models.CASCADE, related_name='faturas')
    mes_referencia = models.CharField(max_length=20)
    arquivo = models.FileField(upload_to='faturas/%Y/%m/')
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vencimento = models.DateField(null=True, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-mes_referencia']
        unique_together = ['unidade_consumidora', 'mes_referencia']