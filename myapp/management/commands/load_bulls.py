from django.core.management.base import BaseCommand
from myapp.utils import load_bulls_from_csv

class Command(BaseCommand):
    help = 'Загружает быков из CSV файла'

    def handle(self, *args, **kwargs):
        load_bulls_from_csv()
        self.stdout.write(self.style.SUCCESS('Данные о быках были успешно загружены.'))
