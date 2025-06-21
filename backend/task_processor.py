#!/usr/bin/env python
# task_processor.py

import os
import django
import threading
import logging
from flask import Flask, request, jsonify

# --- Configuração do Django ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
# --- Fim da Configuração do Django ---

# Importa o serviço APÓS o setup do Django
from api.services.equatorial_service_improved import EquatorialService # Usando a versão melhorada

# Configuração de logging para o task_processor
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='task_processor.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def run_scraping_task(customer_id):
    """
    Função que executa o serviço da Equatorial em uma thread separada.
    """
    logger.info(f"Iniciando tarefa de scraping para o cliente ID: {customer_id}")
    service = None
    try:
        # Instancia o serviço
        service = EquatorialService(customer_id=customer_id)
        
        # Executa o fluxo completo de automação
        # O próprio serviço agora gerencia o setup, login, processamento e fechamento.
        service.processar_todas_faturas() 

        logger.info(f"Tarefa de scraping para o cliente ID: {customer_id} concluída.")

    except Exception as e:
        logger.error(f"Erro CRÍTICO ao executar a tarefa de scraping para o cliente ID: {customer_id}", exc_info=True)
        # A lógica de falha da task agora é tratada dentro do próprio serviço
    finally:
        if service and service.driver:
            logger.info(f"Fechando driver para cliente {customer_id}.")
            service.close()

@app.route('/process-task', methods=['POST'])
def process_task():
    """
    Endpoint que recebe a requisição do Django para iniciar o scraping.
    """
    data = request.get_json()
    if not data or 'customer_id' not in data:
        logger.warning("Recebida requisição inválida sem customer_id")
        return jsonify({"error": "customer_id não fornecido"}), 400

    customer_id = data['customer_id']
    logger.info(f"Requisição recebida para iniciar tarefa para o cliente {customer_id}")
    
    # Inicia a tarefa de scraping em uma nova thread para não bloquear a requisição
    task_thread = threading.Thread(target=run_scraping_task, args=(customer_id,))
    task_thread.start()
    
    return jsonify({"message": f"Tarefa para o cliente {customer_id} iniciada em segundo plano."}), 202

if __name__ == '__main__':
    print("Servidor de tarefas (Flask) rodando em http://127.0.0.1:5001")
    # Usar host '0.0.0.0' para ser acessível de fora do container (do host)
    app.run(host='0.0.0.0', port=5001, debug=True)
