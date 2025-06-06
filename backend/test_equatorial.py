#!/usr/bin/env python
# test_equatorial.py
import os
import django
import logging
import sys

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from api.services.equatorial_service import EquatorialService
from api.models import Customer, FaturaTask, UnidadeConsumidora

def main():
    # Get test customer
    customer = Customer.objects.get(cpf='70120838168')
    logger.info(f"Found customer: {customer.nome} with ID: {customer.id}")
    
    # Get UC
    uc = UnidadeConsumidora.objects.get(codigo='10023560892')
    logger.info(f"Found UC: {uc.codigo}")
    
    # Create task if not exists
    task, created = FaturaTask.objects.get_or_create(
        customer=customer,
        unidade_consumidora=uc,
        defaults={'status': 'pending'}
    )
    if created:
        logger.info(f"Created new task with ID: {task.id}")
    else:
        logger.info(f"Using existing task with ID: {task.id}")
    
    # Initialize service
    service = EquatorialService(customer.id)
    logger.info("Setting up driver...")
    
    try:
        # Setup driver
        setup_success = service.setup_driver()
        logger.info(f"Driver setup: {setup_success}")
        
        if setup_success:
            # Attempt login
            logger.info("Attempting login...")
            login_success = service.login()
            logger.info(f"Login success: {login_success}")
            
            if login_success:
                # Process faturas
                logger.info("Processing faturas...")
                process_success = service.process_faturas()
                logger.info(f"Process success: {process_success}")
            else:
                logger.error("Login failed")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Close driver
        logger.info("Closing driver...")
        service.close()

if __name__ == "__main__":
    main()
