#!/usr/bin/env python
# backend/test_equatorial_improved.py
"""
Script de teste para o serviço Equatorial melhorado
"""

import os
import sys
import django
from datetime import datetime

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Customer, UnidadeConsumidora, FaturaTask
from api.services.equatorial_service import EquatorialService
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('equatorial_improved_test.log')
    ]
)

logger = logging.getLogger(__name__)


def test_improved_service():
    """Testa o serviço melhorado com as técnicas do bot Python"""
    print("=== TESTE DO SERVIÇO EQUATORIAL MELHORADO ===")
    print("-" * 50)
    
    # Dados de teste
    test_data = {
        'uc': '10023560892',
        'cpf': '70120838168',
        'data_nascimento': '09/11/1980',
        'nome': 'Cliente Teste Equatorial'
    }
    
    try:
        # 1. Preparar cliente de teste
        print("\n1. Preparando cliente de teste...")
        
        data_nascimento = datetime.strptime(test_data['data_nascimento'], '%d/%m/%Y').date()
        
        customer, created = Customer.objects.get_or_create(
            cpf=test_data['cpf'],
            defaults={
                'nome': test_data['nome'],
                'cpf_titular': test_data['cpf'],
                'data_nascimento': data_nascimento,
                'endereco': 'Endereço de teste',
                'email': 'teste@teste.com'
            }
        )
        
        if not created:
            # Atualiza dados se necessário
            customer.data_nascimento = data_nascimento
            customer.cpf_titular = test_data['cpf']
            customer.save()
        
        print(f"✓ Cliente: {customer.nome} (ID: {customer.id})")
        
        # 2. Preparar UC
        print("\n2. Preparando UC...")
        
        uc, created = UnidadeConsumidora.objects.get_or_create(
            codigo=test_data['uc'],
            customer=customer,
            defaults={
                'endereco': 'Endereço UC Teste',
                'tipo': 'Residencial'
            }
        )
        
        print(f"✓ UC: {uc.codigo}")
        
        # 3. Limpar tarefas anteriores
        print("\n3. Limpando tarefas anteriores...")
        FaturaTask.objects.filter(customer=customer).delete()
        
        # 4. Criar nova tarefa
        task = FaturaTask.objects.create(
            customer=customer,
            unidade_consumidora=uc,
            status='pending'
        )
        print(f"✓ Tarefa criada: ID {task.id}")
        
        # 5. Inicializar serviço
        print("\n4. Inicializando serviço...")
        service = EquatorialService(customer.id)
        
        # 6. Configurar driver
        print("\n5. Configurando driver...")
        if not service.setup_driver():
            raise Exception("Falha ao configurar driver")
        print("✓ Driver configurado com sucesso")
        
        # 7. Testar login
        print("\n6. Testando login...")
        
        login_success = service.login()
        
        if login_success:
            print("✅ LOGIN REALIZADO COM SUCESSO!")
            
            # 8. Processar faturas
            print("\n7. Processando faturas...")

            process_success = service.process_faturas()
            
            if process_success:
                print("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
                
                # Verificar resultados
                print("\n8. Verificando resultados...")
                
                # Recarrega task
                task.refresh_from_db()
                print(f"   - Status da tarefa: {task.status}")
                
                # Conta faturas baixadas
                faturas = customer.faturas.all()
                print(f"   - Faturas baixadas: {faturas.count()}")
                
                for fatura in faturas:
                    print(f"     • {fatura.mes_referencia} - UC {fatura.unidade_consumidora.codigo}")
                    
            else:
                print("❌ Falha no processamento de faturas")
                
        else:
            print("❌ Falha no login")
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        logger.exception("Erro durante o teste")
        
    finally:
        # Fechar driver
        if 'service' in locals():
            print("\n9. Fechando driver...")
            service.close()
            print("✓ Driver fechado")
    
    print("\n" + "=" * 50)
    print("TESTE CONCLUÍDO")


if __name__ == "__main__":
    test_improved_service()