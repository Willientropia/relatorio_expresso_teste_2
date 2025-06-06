#!/usr/bin/env python
# test_import.py

import os
import django

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import logging
from api.models import Customer, FaturaTask
from api.services.equatorial_service import EquatorialService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='import_test.log',
    filemode='w'
)

logger = logging.getLogger(__name__)

def main():
    # ID do cliente a ser testado
    customer_id = 2
    
    try:
        # Obter cliente
        customer = Customer.objects.get(id=customer_id)
        print(f"Cliente encontrado: {customer.nome}")
        print(f"CPF: {customer.cpf}")
        print(f"Data nascimento: {customer.data_nascimento}")
        
        # Contar tarefas pendentes
        pending_tasks = FaturaTask.objects.filter(customer=customer, status='pending').count()
        print(f"Tarefas pendentes: {pending_tasks}")
        
        # Inicializar serviço Equatorial
        print("Inicializando EquatorialService...")
        service = EquatorialService(customer_id)
        
        # Configurar driver
        print("Configurando driver...")
        setup_success = service.setup_driver()
        print(f"Driver configurado: {setup_success}")
        
        if setup_success:
            # Tentar login
            print("Tentando login...")
            login_success = service.login()
            print(f"Login bem-sucedido: {login_success}")
            
            if login_success:
                # Processar faturas
                print("Processando faturas...")
                process_success = service.process_faturas()
                print(f"Processamento de faturas: {process_success}")
            else:
                print("Falha no login")
        else:
            print("Falha na configuração do driver")
        
        # Fechar driver
        print("Fechando driver...")
        service.close()
        
        # Verificar estado das tarefas após processamento
        completed_tasks = FaturaTask.objects.filter(customer=customer, status='completed').count()
        failed_tasks = FaturaTask.objects.filter(customer=customer, status='failed').count()
        print(f"Tarefas concluídas: {completed_tasks}")
        print(f"Tarefas com falha: {failed_tasks}")
        
    except Exception as e:
        logger.exception("Erro durante o teste")
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    main()
