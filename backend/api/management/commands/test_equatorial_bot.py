from django.core.management.base import BaseCommand
import logging
import time
from api.services.equatorial_service import EquatorialService
from api.models import Customer, UnidadeConsumidora, FaturaTask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('equatorial_test.log')
    ]
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Equatorial bot with specific credentials'
    
    def add_arguments(self, parser):
        parser.add_argument('--uc', type=str, help='Unidade Consumidora')
        parser.add_argument('--cpf', type=str, help='CPF do titular')
        parser.add_argument('--birth_date', type=str, help='Data de nascimento (DD/MM/YYYY)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Equatorial bot test'))
        
        uc_code = options.get('uc', '10023560892')
        cpf = options.get('cpf', '70120838168')
        birth_date = options.get('birth_date', '09/11/1980')
        self.stdout.write(f"Testing with UC: {uc_code}, CPF: {cpf}, Birth Date: {birth_date}")
        
        try:
            from datetime import datetime
            
            # Parse birth date
            birth_date_obj = datetime.strptime(birth_date, '%d/%m/%Y').date()
            
            # Get or create test customer
            customer, created = Customer.objects.get_or_create(
                cpf=cpf,
                defaults={
                    'nome': 'Test Customer', 
                    'email': 'test@example.com',
                    'data_nascimento': birth_date_obj,
                    'cpf_titular': cpf
                }
            )
            
            # Update existing customer if needed
            if not created:
                customer.data_nascimento = birth_date_obj
                customer.cpf_titular = cpf
                customer.save()
            
            self.stdout.write(f"{'Created' if created else 'Found'} customer: {customer.nome} with ID: {customer.id}")
            
            # Get or create UC
            uc, created = UnidadeConsumidora.objects.get_or_create(
                codigo=uc_code,
                defaults={'customer': customer}
            )
            self.stdout.write(f"{'Created' if created else 'Found'} UC: {uc.codigo}")
            
            # Clean up previous tasks
            pending_tasks = FaturaTask.objects.filter(
                customer=customer,
                unidade_consumidora=uc
            )
            if pending_tasks.exists():
                self.stdout.write(f"Found {pending_tasks.count()} existing tasks. Cleaning up...")
                pending_tasks.delete()
            
            # Create new task
            task = FaturaTask.objects.create(
                customer=customer,
                unidade_consumidora=uc,
                status='pending'
            )
            self.stdout.write(f"Created new task with ID: {task.id}")
            
            # Initialize service
            self.stdout.write("Initializing EquatorialService...")
            service = EquatorialService(customer.id)
            
            # Setup driver
            self.stdout.write("Setting up Chrome driver...")
            setup_success = service.setup_driver()
            self.stdout.write(self.style.SUCCESS(f"Driver setup: {setup_success}") if setup_success else self.style.ERROR(f"Driver setup failed"))
            
            if setup_success:
                # Print driver info
                self.stdout.write(f"User Agent: {service.driver.execute_script('return navigator.userAgent')}")
                self.stdout.write(f"WebDriver flag: {service.driver.execute_script('return navigator.webdriver')}")
                
                # Attempt login with retry logic
                max_retries = 3
                login_success = False
                
                for attempt in range(max_retries):
                    self.stdout.write(f"Login attempt {attempt+1}/{max_retries}...")
                    login_success = service.login()
                    
                    if login_success:
                        self.stdout.write(self.style.SUCCESS(f"Login successful on attempt {attempt+1}"))
                        break
                    else:
                        self.stdout.write(self.style.WARNING(f"Login failed on attempt {attempt+1}"))
                        if attempt < max_retries - 1:
                            self.stdout.write("Waiting 10 seconds before retrying...")
                            time.sleep(10)
                
                if login_success:
                    # Process faturas
                    self.stdout.write("Processing faturas...")
                    process_success = service.process_faturas()
                    self.stdout.write(
                        self.style.SUCCESS(f"Faturas processing: {process_success}") 
                        if process_success 
                        else self.style.ERROR(f"Faturas processing failed")
                    )
                else:
                    self.stdout.write(self.style.ERROR("All login attempts failed"))
            
            # Close driver
            self.stdout.write("Closing driver...")
            service.close()
            self.stdout.write(self.style.SUCCESS("Test completed"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            logger.exception("Exception during test")
