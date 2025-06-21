import os
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Fatura
import shutil

class Command(BaseCommand):
    help = 'Deletes all Fatura records and their associated files, and clears the temp folder.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting the process to delete all invoices and clear directories...'))

        # 1. Delete Fatura records from the database
        faturas = Fatura.objects.all()
        faturas_count = faturas.count()

        if faturas_count > 0:
            deleted_count, _ = faturas.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} invoice record(s) from the database.'))
        else:
            self.stdout.write(self.style.SUCCESS('No invoices found in the database.'))

        # 2. Delete all files and subdirectories within the main 'faturas' directory
        faturas_base_dir = os.path.join(settings.MEDIA_ROOT, 'faturas')
        if os.path.exists(faturas_base_dir):
            self.stdout.write(self.style.WARNING(f'Cleaning up directory: {faturas_base_dir}'))
            for item in os.listdir(faturas_base_dir):
                item_path = os.path.join(faturas_base_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        self.stdout.write(f'Deleted directory and all its contents: {item_path}')
                    else:
                        os.remove(item_path)
                        self.stdout.write(f'Deleted file: {item_path}')
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error deleting {item_path}: {e}'))
            self.stdout.write(self.style.SUCCESS(f'Directory {faturas_base_dir} has been cleared.'))
        else:
            self.stdout.write(self.style.WARNING(f'Directory not found, skipping: {faturas_base_dir}'))

        # 3. Clean up the temp_faturas directory
        temp_faturas_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
        if os.path.exists(temp_faturas_dir):
            self.stdout.write(self.style.WARNING(f'Cleaning up temporary directory: {temp_faturas_dir}'))
            for filename in os.listdir(temp_faturas_dir):
                file_path = os.path.join(temp_faturas_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Failed to delete {file_path}. Reason: {e}'))
            self.stdout.write(self.style.SUCCESS(f'Temporary directory {temp_faturas_dir} has been cleared.'))
        else:
            self.stdout.write(self.style.WARNING(f'Temporary directory not found, skipping: {temp_faturas_dir}'))
            
        self.stdout.write(self.style.SUCCESS('Invoice cleanup process finished.'))
