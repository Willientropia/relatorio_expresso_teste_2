#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Customer, FaturaTask, FaturaLog, Fatura

def check_customer_status():
    try:
        customer = Customer.objects.get(cpf='70120838168')
        print('=== CUSTOMER INFO ===')
        print(f'Nome: {customer.nome}')
        print(f'CPF: {customer.cpf}')
        print(f'Data nascimento: {customer.data_nascimento}')
        
        ucs_ativas = customer.unidades_consumidoras.filter(data_vigencia_fim__isnull=True)
        print(f'UCs ativas: {[uc.codigo for uc in ucs_ativas]}')
        print()
        
        print('=== RECENT TASKS ===')
        tasks = FaturaTask.objects.filter(customer=customer).order_by('-created_at')[:5]
        for task in tasks:
            print(f'Task ID {task.id}: UC {task.unidade_consumidora.codigo} - Status: {task.status} - Created: {task.created_at}')
            if task.error_message:
                print(f'  Error: {task.error_message}')
        print()
        
        print('=== RECENT FATURAS ===')
        faturas = Fatura.objects.filter(customer=customer).order_by('-downloaded_at')[:5]
        for fatura in faturas:
            print(f'Fatura: UC {fatura.unidade_consumidora.codigo} - Mês: {fatura.mes_referencia} - Downloaded: {fatura.downloaded_at}')
        print()
        
        print('=== RECENT LOGS ===')
        logs = FaturaLog.objects.filter(customer=customer).order_by('-created_at')[:3]
        for log in logs:
            print(f'Log: CPF {log.cpf_titular} - UCs: {log.ucs_encontradas} - Faturas: {log.faturas_encontradas} - Created: {log.created_at}')
            
    except Customer.DoesNotExist:
        print("Customer with CPF 70120838168 not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_customer_status()
