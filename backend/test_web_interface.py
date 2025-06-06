#!/usr/bin/env python
import os
import sys
import django
import requests
import json
import time

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Customer, FaturaTask

def test_web_interface():
    try:
        # Get customer ID
        customer = Customer.objects.get(cpf='70120838168')
        customer_id = customer.id
        print(f"Testing web interface for customer ID: {customer_id}")
        print(f"Customer: {customer.nome}")
        print(f"Birth date: {customer.data_nascimento}")
        print(f"Active UCs: {[uc.codigo for uc in customer.unidades_consumidoras.filter(data_vigencia_fim__isnull=True)]}")
        print()
        
        # Test API endpoint (assuming Django dev server is running on port 8000)
        base_url = "http://localhost:8000/api"
          # 1. Test start import
        print("=== Testing start_fatura_import API ===")
        url = f"{base_url}/customers/{customer_id}/faturas/import/"
        
        try:
            response = requests.post(url, timeout=10)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 201:
                data = response.json()
                print("✅ Import started successfully!")
                print(f"Message: {data.get('message')}")
                print(f"Tasks created: {len(data.get('tasks', []))}")
                
                # Get task IDs for monitoring
                task_ids = [task['id'] for task in data.get('tasks', [])]
                print(f"Task IDs: {task_ids}")
                
                # 2. Monitor task progress
                print("\n=== Monitoring task progress ===")
                for i in range(30):  # Monitor for 30 seconds
                    print(f"Check {i+1}/30...")
                      # Check task status via API
                    status_url = f"{base_url}/customers/{customer_id}/faturas/tasks/"
                    status_response = requests.get(status_url, timeout=10)
                    
                    if status_response.status_code == 200:
                        tasks = status_response.json()
                        current_tasks = [task for task in tasks if task['id'] in task_ids]
                        
                        print("Current task statuses:")
                        for task in current_tasks:
                            print(f"  Task {task['id']}: {task['status']}")
                            if task.get('error_message'):
                                print(f"    Error: {task['error_message']}")
                        
                        # Check if all tasks are completed or failed
                        if all(task['status'] in ['completed', 'failed'] for task in current_tasks):
                            print("✅ All tasks finished!")
                            break
                    
                    time.sleep(2)  # Wait 2 seconds between checks
                
                # 3. Check faturas
                print("\n=== Checking downloaded faturas ===")
                faturas_url = f"{base_url}/customers/{customer_id}/faturas/"
                faturas_response = requests.get(faturas_url, timeout=10)
                
                if faturas_response.status_code == 200:
                    faturas = faturas_response.json()
                    print(f"Total faturas: {len(faturas)}")
                    for fatura in faturas[:3]:  # Show first 3
                        print(f"  Fatura: UC {fatura.get('unidade_consumidora')} - {fatura.get('mes_referencia')} - {fatura.get('valor')}")
                
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - is the Django server running on localhost:8000?")
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
        except Exception as e:
            print(f"❌ Request error: {e}")
            
    except Customer.DoesNotExist:
        print("❌ Customer with CPF 70120838168 not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_web_interface()
