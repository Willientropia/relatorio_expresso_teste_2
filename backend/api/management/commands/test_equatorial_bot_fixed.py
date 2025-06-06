from django.core.management.base import BaseCommand
import logging
import time
from datetime import datetime
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
            FaturaTask.objects.filter(customer=customer).delete()
            
            # Create task
            task = FaturaTask.objects.create(
                customer=customer,
                unidade_consumidora=uc,
                status='pending'
            )
            self.stdout.write(f"Created task: {task.id}")
            
            # Initialize bot
            service = EquatorialService(customer.id)
            
            # Setup driver
            if not service.setup_driver():
                self.stdout.write(self.style.ERROR('Failed to setup driver'))
                return
            
            self.stdout.write(self.style.SUCCESS('Driver setup completed'))
            
            # Test login
            login_success = service.login()
            
            if login_success:
                self.stdout.write(self.style.SUCCESS('Login successful!'))
                
                # Test processing faturas
                processing_success = service.process_faturas()
                
                if processing_success:
                    self.stdout.write(self.style.SUCCESS('Faturas processing completed successfully!'))
                else:
                    self.stdout.write(self.style.WARNING('Faturas processing completed with some issues'))
                    
            else:
                self.stdout.write(self.style.ERROR('Login failed'))
                
            # Close driver
            service.close()
            
        except Exception as e:
            logger.error(f"Exception during test", exc_info=True)
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            
        self.stdout.write(self.style.SUCCESS('Test completed'))
