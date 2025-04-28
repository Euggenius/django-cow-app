import csv
from datetime import datetime

# Германия - DEU
# США - USA
# Россия - RUS
# Чехия - CHE
# Нидерланды

def convert_country_id(country_id):
    to_cid = {
        "840": "USA",
        "985": "IND",
        "982": "HUN",
        "949": "ESP",
        "988": "IRN",
        "124": "CAN"
    }

    if country_id in to_cid:
        country_id = to_cid[country_id]

    country_dict = {
        "DEU": "DE",
        "USA": "US",
        "RUS": "RU",
        "CHE": "CZ",
        "NLD": "NL",
        "CAN": "CA",
    }

    return country_dict.get(country_id, f"UNKNOWN_{country_id}")

def read_selected_fields(file_path, num_bulls=756000, output_file="/Users/evgenijbojko/jango_site/eug/bulls.csv"):
    # unic_id=set()
    with open(file_path, 'rb') as file:
        positions = {
            "Registered name": (99, 128),
            "Birth date": (89, 96),
            "Breed code": (4, 5),
            "CountryID": (6, 8),
            "Inventary number": (9, 20),
            "PTA milk": (238, 242),
            "PTA fat": (245, 248),
            "PTA protein": (254, 257),
            "PTA productive life (PL)": (263, 265),
            "PTA SCS": (268, 270),
            "PTA DPR": (290, 292),
            "PTA HCR": (568, 571),
            "PTA CCR": (586, 589),
            "PTA Gestation Length": (654, 656),
            "PTA Milk Fever": (675, 678),
            "PTA Displaced abomasum": (698, 701),
            "PTA Ketosis": (721, 724),
            "PTA Mastitis": (744, 747),
            "PTA Metritis": (767, 770),
            "PTA Retained placenta": (790, 793),
            "PTA Early First Calving": (813, 816),
            "PTA Heifer Livability": (836, 839),
            "PTA Feed Saved": (859, 863),
            "PTA Residual Feed Intake": (884, 888)
        }

        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                "bull_id", 'breed', 'country_id', "registered_name", "birth_date", "inventary_number", "identification_number",
                "pta_milk", "pta_fat", "pta_protein", "pta_productive_life", "pta_scs", 
                "pta_dpr", "pta_hcr", "pta_ccr", "pta_gestation_length", "pta_milk_fever", 
                "pta_displaced_abomasum", "pta_ketosis", "pta_mastitis", "pta_metritis", 
                "pta_retained_placenta", "pta_early_first_calving", "pta_heifer_livability", 
                "pta_feed_saved", "pta_residual_feed_intake"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for bull_ind in range(1, num_bulls + 1):
                print(f"Processing bull {bull_ind}...")
                offset = bull_ind - 1 
                bull_id = f"BULL_{bull_ind}"
                data_row = {"bull_id": bull_id}

                for field, (start, end) in positions.items():
                    start_with_offset = start + offset * 909
                    end_with_offset = end + offset * 909

                    file.seek(start_with_offset - 1)
                    data = file.read(end_with_offset - start_with_offset + 1)

                    res = data.decode('utf-8').strip()

                    if field == "Registered name":
                        data_row["registered_name"] = res
                    elif field == "Birth date":
                        try:
                            birth_date = datetime.strptime(res, "%Y%m%d").date()
                            data_row["birth_date"] = birth_date
                        except ValueError:
                            data_row["birth_date"] = None
                    elif field == "Inventary number":
                        data_row["inventary_number"] = res
                    elif field == "Breed code":
                        # if res not in unic_id:
                        #     print(res)
                        #     unic_id.add(res)
                        data_row["breed"] = res
                    elif field == "CountryID":
                        data_row["country_id"] = res
                        # if res not in unic_id:
                        #     print(res)
                        #     unic_id.add(res)
                

                pta_values = {}
                for field, (start, end) in positions.items():
                    if field not in ["Registered name", "Birth date", "CountryID", "Breed code", "Inventary number"]:
                        start_with_offset = start + offset * 909
                        end_with_offset = end + offset * 909

                        file.seek(start_with_offset - 1)
                        data = file.read(end_with_offset - start_with_offset + 1)

                        res = data.decode('utf-8').strip()
                        res = res.split()
                        res = int(res[0]) if res else 0
                        pta_values[field] = res

                data_row['identification_number'] = convert_country_id(data_row['country_id']) + data_row['inventary_number'][2:]
                data_row['pta_milk'] = pta_values.get("PTA milk", 0)
                data_row['pta_fat'] = pta_values.get("PTA fat", 0)
                data_row['pta_protein'] = pta_values.get("PTA protein", 0)
                data_row['pta_productive_life'] = pta_values.get("PTA productive life (PL)", 0)
                data_row['pta_scs'] = pta_values.get("PTA SCS", 0)
                data_row['pta_dpr'] = pta_values.get("PTA DPR", 0)
                data_row['pta_hcr'] = pta_values.get("PTA HCR", 0)
                data_row['pta_ccr'] = pta_values.get("PTA CCR", 0)
                data_row['pta_gestation_length'] = pta_values.get("PTA Gestation Length", 0)
                data_row['pta_milk_fever'] = pta_values.get("PTA Milk Fever", 0)
                data_row['pta_displaced_abomasum'] = pta_values.get("PTA Displaced abomasum", 0)
                data_row['pta_ketosis'] = pta_values.get("PTA Ketosis", 0)
                data_row['pta_mastitis'] = pta_values.get("PTA Mastitis", 0)
                data_row['pta_metritis'] = pta_values.get("PTA Metritis", 0)
                data_row['pta_retained_placenta'] = pta_values.get("PTA Retained placenta", 0)
                data_row['pta_early_first_calving'] = pta_values.get("PTA Early First Calving", 0)
                data_row['pta_heifer_livability'] = pta_values.get("PTA Heifer Livability", 0)
                data_row['pta_feed_saved'] = pta_values.get("PTA Feed Saved", 0)
                data_row['pta_residual_feed_intake'] = pta_values.get("PTA Residual Feed Intake", 0)

                writer.writerow(data_row)

def load_bulls_from_csv():
    from myapp.models import Bull
    file_path = '/Users/evgenijbojko/jango_site/eug/bulls.csv'
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            name_counter = 1
            for row in reader:
                if not row.get('registered_name'):
                    reg_name = f"NONAME-BULL-{name_counter}"
                    name_counter += 1
                else: reg_name = row['registered_name']

                identification_number = row.get('identification_number')
                # if not identification_number:
                #     print("Пропускаем строку: нет идентификатора быка.")
                #     continue

                try:
                    bull=Bull.objects.get(identification_number=identification_number)
                    print(bull)
                    print(row)
                    print()

                    # print(f"Бык с идентификатором {identification_number} уже существует, пропускаем.")
                    continue
                except Bull.DoesNotExist:
                    pass

                Bull.objects.get_or_create(
                    registered_name=reg_name,
                    identification_number=identification_number,
                    birth_date=row.get('birth_date', None),
                    pta_milk=row.get('pta_milk', 0),
                    pta_fat=row.get('pta_fat', 0),
                    pta_protein=row.get('pta_protein', 0),
                    pta_productive_life=row.get('pta_productive_life', 0),
                    pta_scs=row.get('pta_scs', 0),
                    pta_dpr=row.get('pta_dpr', 0),
                    pta_hcr=row.get('pta_hcr', 0),
                    pta_ccr=row.get('pta_ccr', 0),
                    pta_gestation_length=row.get('pta_gestation_length', 0),
                    pta_milk_fever=row.get('pta_milk_fever', 0),
                    pta_displaced_abomasum=row.get('pta_displaced_abomasum', 0),
                    pta_ketosis=row.get('pta_ketosis', 0),
                    pta_mastitis=row.get('pta_mastitis', 0),
                    pta_metritis=row.get('pta_metritis', 0),
                    pta_retained_placenta=row.get('pta_retained_placenta', 0),
                    pta_early_first_calving=row.get('pta_early_first_calving', 0),
                    pta_heifer_livability=row.get('pta_heifer_livability', 0),
                    pta_feed_saved=row.get('pta_feed_saved', 0),
                    pta_residual_feed_intake=row.get('pta_residual_feed_intake', 0),
                )

                # print(f"Добавлен новый бык: {bull.identification_number}")
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")

if __name__=="__main__":
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT sqlite_version();")
        print(cursor.fetchone())