#!/usr/bin/env python3
"""
Test script for the corrected Equatorial bot functionality
Tests with the provided credentials:
- UC: 10023560892
- CPF: 70120838168
- Data de nascimento: 09/11/1980
"""

import os
import sys
import django
from datetime import datetime

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Customer, UnidadeConsumidora
from api.services.equatorial_service import EquatorialService
import logging

# Configurar logging para ver detalhes
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_equatorial_bot():
    """Testa o bot Equatorial com as credenciais fornecidas"""
    print("=== TESTE DO BOT EQUATORIAL CORRIGIDO ===")
    
    # Dados de teste
    test_data = {
        'uc': '10023560892',
        'cpf': '70120838168',
        'data_nascimento': '09/11/1980',
        'nome': 'Cliente Teste Equatorial'
    }
    
    try:
        # 1. Criar ou buscar cliente de teste
        print(f"\n1. Configurando cliente de teste...")
        
        # Converter data de nascimento para formato datetime
        data_nascimento = datetime.strptime(test_data['data_nascimento'], '%d/%m/%Y').date()
        
        customer, created = Customer.objects.get_or_create(
            cpf=test_data['cpf'],
            defaults={
                'nome': test_data['nome'],
                'cpf_titular': test_data['cpf'],
                'data_nascimento': data_nascimento,
                'endereco': 'Endereço de teste'
            }
        )
        
        if created:
            print(f"✓ Cliente criado: {customer.nome} (ID: {customer.id})")
        else:
            print(f"✓ Cliente encontrado: {customer.nome} (ID: {customer.id})")
            # Atualizar data de nascimento se necessário
            if not customer.data_nascimento:
                customer.data_nascimento = data_nascimento
                customer.save()
                print("✓ Data de nascimento atualizada")
        
        # 2. Criar ou buscar UC de teste        print(f"\n2. Configurando UC de teste...")
        
        uc, created = UnidadeConsumidora.objects.get_or_create(
            codigo=test_data['uc'],
            defaults={
                'customer': customer,
                'endereco': 'Endereço UC Teste'
            }
        )
        
        if created:            print(f"✓ UC criada: {uc.codigo}")
        else:
            print(f"✓ UC encontrada: {uc.codigo}")
        
        # 3. Testar o serviço Equatorial
        print(f"\n3. Iniciando teste do bot Equatorial...")
        print(f"   UC: {test_data['uc']}")
        print(f"   CPF: {test_data['cpf']}")
        print(f"   Data nascimento: {test_data['data_nascimento']}")
        
        service = EquatorialService(customer.id)
        
        # 4. Configurar driver
        print(f"\n4. Configurando driver do Chrome...")
        if not service.setup_driver():
            raise Exception("Falha ao configurar driver do Chrome")
        print("✓ Driver configurado com sucesso")
        
        # 5. Testar login
        print(f"\n5. Testando processo de login (2 etapas)...")
        login_success = service.login()
        
        if login_success:
            print("✅ LOGIN REALIZADO COM SUCESSO!")
            
            # 6. Testar busca de UCs
            print(f"\n6. Testando busca de UCs disponíveis...")
            try:
                ucs = service.get_all_ucs_from_dropdown()
                print(f"✓ UCs encontradas: {len(ucs)}")
                for uc_info in ucs:
                    print(f"   - {uc_info}")
            except Exception as e:
                print(f"⚠️  Erro ao buscar UCs: {e}")
            
            # 7. Testar download de faturas
            print(f"\n7. Testando download de faturas...")
            try:
                # Configurar UCs alvo
                service.target_ucs = [test_data['uc']]
                
                # Processar faturas
                service.process_faturas()
                print("✅ PROCESSO DE DOWNLOAD CONCLUÍDO!")
                
            except Exception as e:
                print(f"❌ Erro no download de faturas: {e}")
                
        else:
            print("❌ FALHA NO LOGIN")
            
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Fechar driver
        try:
            if 'service' in locals() and service.driver:
                service.close()
                print("\n✓ Driver fechado")
        except:
            pass

if __name__ == "__main__":
    test_equatorial_bot()
