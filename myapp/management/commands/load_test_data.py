import csv
from myapp.models import Bull

def load_bulls_from_csv():
    file_path = 'bulls.csv'
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if not row.get('bull_id') or not row.get('registered_name'):
                    continue

                bull, created = Bull.objects.get_or_create(
                    bull_id=row['bull_id'],
                    registered_name=row['registered_name'],
                    birth_date=row.get('birth_date', None),
                    identification_number=row.get('identification_number', None),
                    pta_milk=row.get('pta_milk', 0),
                    pta_fat=row.get('pta_fat', 0),
                    pta_protein=row.get('pta_protein', 0),
                )
                if created:
                    print(f"Добавлен новый бык: {bull.bull_id}")
                else:
                    print(f"Бык с bull_id={bull.bull_id} уже существует в базе.")

    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
