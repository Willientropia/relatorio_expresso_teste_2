# backend/api/migrations/0003_customer_updates.py
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_unidadeconsumidora'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='cpf_titular',
            field=models.CharField(blank=True, max_length=14, null=True, verbose_name='CPF do Titular da UC'),
        ),
        migrations.AddField(
            model_name='customer',
            name='data_nascimento',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='FaturaTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pendente'), ('processing', 'Processando'), ('completed', 'Concluída'), ('failed', 'Falhou')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fatura_tasks', to='api.customer')),
                ('unidade_consumidora', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.unidadeconsumidora')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FaturaLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpf_titular', models.CharField(max_length=14)),
                ('ucs_encontradas', models.JSONField(default=list)),
                ('faturas_encontradas', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fatura_logs', to='api.customer')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Fatura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes_referencia', models.CharField(max_length=20)),
                ('arquivo', models.FileField(upload_to='faturas/%Y/%m/')),
                ('valor', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('vencimento', models.DateField(blank=True, null=True)),
                ('downloaded_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faturas', to='api.customer')),
                ('unidade_consumidora', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faturas', to='api.unidadeconsumidora')),
            ],
            options={
                'ordering': ['-mes_referencia'],
                'unique_together': {('unidade_consumidora', 'mes_referencia')},
            },
        ),
    ]