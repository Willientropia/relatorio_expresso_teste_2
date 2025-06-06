#!/usr/bin/env python
# task_processor.py

import os
import django
import time

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import logging
from api.models import FaturaTask
from api.services.equatorial_service import EquatorialService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='task_processor.log',
    filemode='w'
)

logger = logging.getLogger(__name__)

def process_tasks():
    """
    Processa todas as tarefas pendentes no banco de dados
    """
    # Encontrar tarefas pendentes, agrupadas por cliente
    customer_ids = FaturaTask.objects.filter(status='pending').values_list('customer_id', flat=True).distinct()
    
    if not customer_ids:
        print("Nenhuma tarefa pendente encontrada")
        return
    
    print(f"Encontradas tarefas pendentes para {len(customer_ids)} clientes")
    
    # Processar cada cliente
    for customer_id in customer_ids:
        print(f"Processando cliente ID: {customer_id}")
        
        # Obter tarefas pendentes do cliente
        tasks = FaturaTask.objects.filter(customer_id=customer_id, status='pending')
        print(f"  {tasks.count()} tarefas pendentes")
        
        # Marcar tarefas como em processamento
        tasks.update(status='processing')
        
        try:
            # Inicializar serviço
            service = EquatorialService(customer_id)
            
            success = False
            try:
                # Configurar driver
                print("  Configurando driver...")
                if service.setup_driver():
                    # Fazer login
                    print("  Tentando login...")
                    if service.login():
                        # Processar faturas
                        print("  Processando faturas...")
                        success = service.process_faturas()
                    else:
                        print("  Falha no login")
                else:
                    print("  Falha na configuração do driver")
            finally:
                # Fechar driver
                print("  Fechando driver...")
                service.close()
            
            if not success:
                # Atualizar tarefas como falhas se o processamento não foi bem-sucedido
                print("  Atualizando tarefas como falhas")
                tasks.update(status='failed', error_message='Falha no processamento das faturas')
        
        except Exception as e:
            logger.exception(f"Erro ao processar tarefas para o cliente {customer_id}")
            print(f"  Erro: {str(e)}")
            # Atualizar tarefas como falhas
            tasks.update(status='failed', error_message=str(e))

if __name__ == "__main__":
    print("Iniciando processador de tarefas...")
    process_tasks()
    print("Processamento concluído")
