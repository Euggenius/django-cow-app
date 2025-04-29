from django.shortcuts import render, redirect
from .models import Bull
from .forms import CsvUploadForm, BullSortForm, PairingForm
import plotly.graph_objects as go
import numpy as np
import scipy.stats as st 
import csv
from io import TextIOWrapper
from django.contrib import messages
import json
from django.http import HttpResponse
from django.db.models import Q, F
from . import matcher
from . import pareto_utils
import random


def format_button_name(name, width=20):
    return name[:width] if len(name) > width else name.ljust(width)


def index(request):
    return render(request, 'myapp/index.html')


def upload(request):
    if request.method == 'POST':
        request.session.flush()
        
        form = CsvUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "Загруженный файл не является CSV. Пожалуйста, выберите файл с расширением .csv")
                return render(request, 'myapp/upload.html', {'form': form})
                
            if csv_file.size > 10 * 1024 * 1024:
                messages.error(request, "Размер файла превышает 10MB. Пожалуйста, загрузите файл меньшего размера.")
                return render(request, 'myapp/upload.html', {'form': form})
            
            try:
                file_content = csv_file.read()
                
                from io import StringIO, TextIOWrapper
                csv_data = csv.DictReader(StringIO(file_content.decode('utf-8')))
                
                required_headers = ['Инвентарный номер', 'Идентификац.№ предка - O', 
                                   'Идентификац.№ предка - OM', 'Идентификац.№ предка - OMM']
                csv_headers = csv_data.fieldnames
                
                if not csv_headers:
                    messages.error(request, "CSV файл пуст или имеет неверный формат.")
                    return render(request, 'myapp/upload.html', {'form': form})
                
                missing_headers = [header for header in required_headers if header not in csv_headers]
                if missing_headers:
                    messages.error(request, f"В CSV файле отсутствуют обязательные колонки: {', '.join(missing_headers)}")
                    return render(request, 'myapp/upload.html', {'form': form})
                
                csv_data = csv.DictReader(StringIO(file_content.decode('utf-8')))
                
                uploaded_cows = {}
                row_count = 0
                valid_rows = 0
                invalid_rows = []

                pta_keys = [value for value, label in BullSortForm.PTA_CHOICES]
                missing_counts = { key: 0 for key in pta_keys }

                for row_index, row in enumerate(csv_data, 1):
                    row_count += 1
                    if row.get('Инвентарный номер') and row.get('Идентификац.№ предка - O') and row.get('Идентификац.№ предка - OM') and row.get('Идентификац.№ предка - OMM'):
                        valid_rows += 1
                        cow_data = {
                            'bull_id': row['Идентификац.№ предка - O'],
                            'maternal_grandfather_id': row['Идентификац.№ предка - OM'],
                            'great_grandfather_id': row['Идентификац.№ предка - OMM'],
                        }
                        uploaded_cows[row['Инвентарный номер']] = cow_data

                        try:
                            father = Bull.objects.get(identification_number=cow_data['bull_id'])
                        except Bull.DoesNotExist:
                            invalid_rows.append(f"Строка {row_index}: Отец (ID: {cow_data['bull_id']}) не найден в базе данных")
                            father = None
                        try:
                            maternal_grandfather = Bull.objects.get(identification_number=cow_data['maternal_grandfather_id'])
                        except Bull.DoesNotExist:
                            invalid_rows.append(f"Строка {row_index}: Дед по матери (ID: {cow_data['maternal_grandfather_id']}) не найден в базе данных")
                            maternal_grandfather = None
                        try:
                            great_grandfather = Bull.objects.get(identification_number=cow_data['great_grandfather_id'])
                        except Bull.DoesNotExist:
                            invalid_rows.append(f"Строка {row_index}: Прадед (ID: {cow_data['great_grandfather_id']}) не найден в базе данных")
                            great_grandfather = None

                        if father is None or maternal_grandfather is None or great_grandfather is None:
                            continue
                        
                        for pta in pta_keys:
                            if not getattr(father, pta, 0) or not getattr(maternal_grandfather, pta, 0) or not getattr(great_grandfather, pta, 0):
                                missing_counts[pta] += 1
                    else:
                        missing_fields = []
                        if not row.get('Инвентарный номер'):
                            missing_fields.append('Инвентарный номер')
                        if not row.get('Идентификац.№ предка - O'):
                            missing_fields.append('Идентификац.№ предка - O')
                        if not row.get('Идентификац.№ предка - OM'):
                            missing_fields.append('Идентификац.№ предка - OM')
                        if not row.get('Идентификац.№ предка - OMM'):
                            missing_fields.append('Идентификац.№ предка - OMM')
                        
                        if missing_fields:
                            invalid_rows.append(f"Строка {row_index}: Отсутствуют поля {', '.join(missing_fields)}")
                        print("Некорректная строка:", row)
                
                if row_count == 0:
                    messages.error(request, "CSV файл не содержит данных.")
                    return render(request, 'myapp/upload.html', {'form': form})
                
                if valid_rows == 0:
                    messages.error(request, "В файле не найдено ни одной корректной строки с данными.")
                    return render(request, 'myapp/upload.html', {'form': form})
                
                invalid_count = row_count - valid_rows
                
                if invalid_count > 0:
                    messages.success(request, f"Найдено {invalid_count} некорректных строк.\nЗагружено {valid_rows} коров из {row_count} строк файла.")
                else:
                    messages.success(request, f"Загружено {valid_rows} коров из {row_count} строк файла.")
                
                request.session['uploaded_cows'] = uploaded_cows
                request.session['missing_counts'] = missing_counts

                return redirect('sort_bulls')
                
            except UnicodeDecodeError:
                messages.error(request, "Ошибка кодировки файла. Пожалуйста, убедитесь, что файл сохранен в кодировке UTF-8.")
                return render(request, 'myapp/upload.html', {'form': form})
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Ошибка при обработке файла: {str(e)}")
                return render(request, 'myapp/upload.html', {'form': form})
    else:
        form = CsvUploadForm()

    return render(request, 'myapp/upload.html', {'form': form})


def optimal_pairing_form(request):
    if 'uploaded_cows' not in request.session or not request.session['uploaded_cows']:
        messages.warning(request, "Сначала загрузите CSV файл с данными коров.")
        return redirect('upload')

    form = PairingForm()
    num_cows_in_session = len(request.session.get('uploaded_cows', {}))
    context = {
        'form': form,
        'num_cows_in_session': num_cows_in_session
    }
    return render(request, 'myapp/optimal_pairing_form.html', context)


def run_optimal_pairing(request):
    if request.method != 'POST':
        return redirect('optimal_pairing_form')

    uploaded_cows_ancestors_dict = request.session.get('uploaded_cows', {})
    if not uploaded_cows_ancestors_dict:
        messages.error(request, "Данные о коровах не найдены в сессии. Пожалуйста, загрузите файл заново.")
        return redirect('upload')

    form = PairingForm(request.POST)
    num_cows_in_session = len(uploaded_cows_ancestors_dict)

    if form.is_valid():
        N_target = form.cleaned_data['num_cows_to_breed']
        B_budget = form.cleaned_data['budget']

        U_CANDIDATE_POOL_SIZE = 5000

        all_bulls_qs = Bull.objects.all()

        valid_cows_ancestors_list = []
        skipped_cow_count = 0
        print(f"Проверка предков для {num_cows_in_session} коров...")
        father_ids = set(d['bull_id'] for d in uploaded_cows_ancestors_dict.values())
        mgf_ids = set(d['maternal_grandfather_id'] for d in uploaded_cows_ancestors_dict.values())
        ggf_ids = set(d['great_grandfather_id'] for d in uploaded_cows_ancestors_dict.values())
        all_ancestor_ids = father_ids | mgf_ids | ggf_ids

        print(f"  Загрузка {len(all_ancestor_ids)} уникальных предков из БД...")
        ancestors_in_db = {
            b.identification_number: b
            for b in Bull.objects.filter(identification_number__in=all_ancestor_ids)
        }
        print(f"  Загружено {len(ancestors_in_db)} предков.")

        for cow_id, ancestors_ids in uploaded_cows_ancestors_dict.items():
            father = ancestors_in_db.get(ancestors_ids['bull_id'])
            mgf = ancestors_in_db.get(ancestors_ids['maternal_grandfather_id'])
            ggf = ancestors_in_db.get(ancestors_ids['great_grandfather_id'])

            if father and mgf and ggf:
                valid_cows_ancestors_list.append({
                    'cow_id': cow_id, 'father': father, 'mgf': mgf, 'ggf': ggf
                })
            else:
                skipped_cow_count += 1

        num_valid_cows = len(valid_cows_ancestors_list)
        print(f"Найдено полных предков для {num_valid_cows} коров. Пропущено: {skipped_cow_count}.")

        if num_valid_cows == 0:
            messages.error(request, "Не найдено ни одной коровы с полными данными предков в базе быков.")
            return render(request, 'myapp/optimal_pairing_form.html', {'form': form, 'num_cows_in_session': num_cows_in_session})

        actual_N = min(N_target, num_valid_cows)
        if N_target > num_valid_cows:
             messages.warning(request, f"Запрошено {N_target} коров, но только для {num_valid_cows} найдены полные данные предков. Расчет будет произведен для {actual_N}.")

        try:
            assignments, net_profit = matcher.run_optimal_pairing(
                all_bulls_qs=all_bulls_qs,
                valid_cows_ancestors=valid_cows_ancestors_list,
                N_target=actual_N,
                B_budget=B_budget
            )

            context = {
                'assignments': assignments,
                'net_profit': net_profit,
                'num_cows_assigned': len(assignments),
                'num_bulls_used': len(set(a['bull'].id for a in assignments)),
                'target_n': N_target,
                'actual_n': actual_N,
                'budget': B_budget,
                'cost_per_bull': matcher.COST_PER_BULL_O
            }
            return render(request, 'myapp/optimal_pairing_results.html', context)

        except Exception as e:
            messages.error(request, f"Ошибка при выполнении алгоритма подбора: {e}")
            import traceback
            traceback.print_exc()
            return render(request, 'myapp/optimal_pairing_form.html', {'form': form, 'num_cows_in_session': num_cows_in_session})

    else:
        messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
        return render(request, 'myapp/optimal_pairing_form.html', {'form': form, 'num_cows_in_session': num_cows_in_session})


def pick_bulls(request):
    # MAX_SELECTION = 5
    session = request.session

    session.setdefault('selected_bulls', [])
    session.setdefault('current_pareto', [])
    session.setdefault('original_order', [])
    session.setdefault('thresholds', [])

    if request.method == 'POST':
        if 'reset' in request.POST:
            if 'selected_bulls' in request.session:
                del request.session['selected_bulls']
            return redirect(request.path)
        
        selected_ids = request.POST.getlist('bull_id')
        session['selected_bulls'] = [str(sid) for sid in selected_ids]
        session.modified = True

        if 'action' in request.POST and request.POST['action'] == 'plot':
            if len(selected_ids) == 5:
                return redirect('plot_results')
            else:
                messages.error(request, "Выберите ровно 5 быков")

        session['current_pareto'] = []
        session.modified = True
        return redirect('pick_bulls') 

    original_order = session['original_order']
    thresholds = session['thresholds']
    selected_bulls_ids = set(session['selected_bulls'])

    if not original_order:
        messages.info(request, "Пожалуйста, выберите критерии сортировки на предыдущем шаге.")
        return render(request, 'myapp/pick_form.html', {'sorted_bulls': [], 'selected_count': 0, 'selected_bulls': [], 'original_order': [], 'thresholds': []})

    if not session['current_pareto']:
        print("Calculating Pareto front...")
        bulls_qs = Bull.objects.all()
        filter_query = Q()
        negative_traits = pareto_utils.NEGATIVE_TRAITS 
        for trait, threshold in zip(original_order, thresholds):
            if threshold is not None:
                try:
                    threshold_val = float(threshold) 
                    if trait in negative_traits:
                        filter_query &= Q(**{trait + '__lte': threshold_val})
                    else:
                        filter_query &= Q(**{trait + '__gte': threshold_val})
                except (ValueError, TypeError):
                     messages.warning(request, f"Некорректное пороговое значение '{threshold}' для '{trait}'. Проигнорировано.")

        filtered_bulls_qs = bulls_qs.filter(filter_query)
        initial_count = filtered_bulls_qs.count()
        print(f"Bulls after threshold filtering: {initial_count}")

        fields_for_pareto = ['id'] + original_order

        all_filtered_data = list(filtered_bulls_qs.values_list(*fields_for_pareto))
        print(f"Retrieved data for {len(all_filtered_data)} bulls.")

        bull_data_for_pareto = all_filtered_data
        
        MAX_BULLS_FOR_PARETO = 10000 
        if initial_count > MAX_BULLS_FOR_PARETO:
            messages.warning(request, f"Найдено слишком много быков ({initial_count}), будет выполнен расчет Парето на случайной выборке из {MAX_BULLS_FOR_PARETO}.")
            print(f"Sampling {MAX_BULLS_FOR_PARETO} bulls randomly from {initial_count}...")
            if initial_count > 0:
                 bull_data_for_pareto = random.sample(all_filtered_data, MAX_BULLS_FOR_PARETO)
            else:
                 bull_data_for_pareto = []
            print(f"Sampled data size: {len(bull_data_for_pareto)}")
        
        pareto_bull_ids = pareto_utils.find_pareto_front(bull_data_for_pareto, original_order)
        
        session['current_pareto'] = [str(pid) for pid in pareto_bull_ids]
        session.modified = True
        print(f"Calculated Pareto Front Size: {len(session['current_pareto'])} based on {len(bull_data_for_pareto)} bulls.")

    BULLS_TO_DISPLAY = 50 
    bull_ids_in_pareto = session['current_pareto']
    bull_ids_to_display = bull_ids_in_pareto[:BULLS_TO_DISPLAY]
    
    required_fields = list(set(['id', 'registered_name'] + original_order))
    bulls_map = {str(b.id): b for b in Bull.objects.filter(id__in=bull_ids_to_display).only(*required_fields)}

    ordered_bulls_to_display = [bulls_map[bid] for bid in bull_ids_to_display if bid in bulls_map]

    context = {
        'sorted_bulls': ordered_bulls_to_display,
        'selected_count': len(request.session.get('selected_bulls', [])),
        'selected_bulls': selected_bulls_ids,
        'original_order': original_order,
        'thresholds': thresholds 
    }
    
    return render(request, 'myapp/pick_form.html', context)


def plot_results(request):
    selected_ids = request.session.get('selected_bulls', [])
    order = request.session.get('original_order', [])
    thresholds = request.session.get('thresholds', [])
    uploaded_cows = request.session.get('uploaded_cows', {})

    if not selected_ids or not order:
        messages.error(request, "Необходимо выбрать быков и параметры сортировки")
        return redirect('upload')

    try:
        base_query = Q(id__in=selected_ids)

        for pta_attribute, threshold in zip(order, thresholds):
            if threshold is not None:
                if pta_attribute in {'pta_scs', 'pta_residual_feed_intake', 
                                'pta_milk_fever', 'pta_displaced_abomasum',
                                'pta_ketosis', 'pta_mastitis', 'pta_metritis',
                                'pta_retained_placenta', 'pta_gestation_length'}:
                    base_query &= Q(**{pta_attribute + '__lte': threshold})
                else:
                    base_query &= Q(**{pta_attribute + '__gte': threshold})

        filtered_bulls = Bull.objects.filter(base_query).order_by('-' + order[0])
        top_5_bulls = filtered_bulls[:5]
        # top_5_bulls = Bull.objects.filter(id__in=selected_ids)[:5]

        # print(uploaded_cows)
        
        cow_data_dict = {}
        cow_scores = {pta: [] for pta in order}
        cid = 1
        ct=0

        for cow_id, cow_data in uploaded_cows.items():
            # print(f"Processing cow {cid}")
            cid += 1
            try:
                father = Bull.objects.get(identification_number=cow_data['bull_id'])
            except Bull.DoesNotExist:
                father = None
                # print(f"Отец с bull_id {cow_data['bull_id']} не найден, пропуск коровы {cow_id}")

            try:
                maternal_grandfather = Bull.objects.get(identification_number=cow_data['maternal_grandfather_id'])
            except Bull.DoesNotExist:
                maternal_grandfather = None
                # print(f"Отец по материнской линии с bull_id {cow_data['maternal_grandfather_id']} не найден, пропуск коровы {cow_id}")

            try:
                great_grandfather = Bull.objects.get(identification_number=cow_data['great_grandfather_id'])
            except Bull.DoesNotExist:
                great_grandfather = None
                # print(f"Отец матери матери с bull_id {cow_data['great_grandfather_id']} не найден, пропуск коровы {cow_id}")

            if father is None or maternal_grandfather is None or great_grandfather is None:
                continue
            ct+=1

            cow_data_dict[cow_id] = {
                'father': father,
                'maternal_grandfather': maternal_grandfather,
                'great_grandfather': great_grandfather
            }

            for pta in order:
                cow_score = (
                    getattr(father, pta, 0) * 0.5 + 
                    getattr(maternal_grandfather, pta, 0) * 0.25 + 
                    getattr(great_grandfather, pta, 0) * 0.125
                )
                cow_scores[pta].append(cow_score)
        print(ct)

        bull_data = {pta: [] for pta in order}
        for bull in top_5_bulls:
            for pta in order:
                values = []
                for cow_id, ancestors in cow_data_dict.items():
                    father = ancestors['father']
                    maternal_grandfather = ancestors['maternal_grandfather']
                    great_grandfather = ancestors['great_grandfather']

                    score = (
                        getattr(bull, pta, 0) * 0.5 + 
                        getattr(father, pta, 0) * 0.25 +
                        getattr(maternal_grandfather, pta, 0) * 0.125 +
                        getattr(great_grandfather, pta, 0) * 0.0625
                    )
                    values.append(score)
                
                bull_data[pta].append({'bull_id': bull.registered_name, 'values': values})

        fig = go.Figure()
        colors = ['red', 'blue', 'green', 'orange', 'purple']

        for pta in order:
            for i, data in enumerate(bull_data[pta]):
                bull_id = data['bull_id']
                values = data['values']
                if not values:
                    continue
                arr = np.array(values, dtype=float)
                kde = st.gaussian_kde(arr)
                x_min, x_max = arr.min(), arr.max()
                margin = (x_max - x_min) * 0.1 if x_max != x_min else 1
                x = np.linspace(x_min - margin, x_max + margin, 200)
                y = kde(x)

                fig.add_trace(go.Scatter(
                    x=x,
                    y=y,
                    mode='lines',
                    name=f"{bull_id} ({pta})",
                    line=dict(color=colors[i % len(colors)], width=3),
                    opacity=0.3,
                    visible=(pta == order[0]) 
                ))

            if cow_scores[pta]:
                cow_arr = np.array(cow_scores[pta], dtype=float)
                cow_kde = st.gaussian_kde(cow_arr)
                cow_x_min, cow_x_max = cow_arr.min(), cow_arr.max()
                cow_margin = (cow_x_max - cow_x_min) * 0.1 if cow_x_max != cow_x_min else 1
                cow_x = np.linspace(cow_x_min - cow_margin, cow_x_max + cow_margin, 200)
                cow_y = cow_kde(cow_x)

                fig.add_trace(go.Scatter(
                    x=cow_x,
                    y=cow_y,
                    mode='lines',
                    name=f"Cows ({pta})",
                    line=dict(color='black', width=3),
                    opacity=0.3,
                    visible=(pta == order[0])
                ))

        block_size = len(top_5_bulls) + 1
        total_traces = len(order) * block_size

        def get_visible_array_for_pta(pta_index):
            vis = [False] * total_traces
            start = pta_index * block_size
            for i in range(start, start + block_size):
                vis[i] = True
            return vis

        def get_visible_array_for_bull(pta_index, bull_index):
            vis = [False] * total_traces
            start = pta_index * block_size
            vis[start + bull_index] = True
            return vis

        current_pta_index = 0

        pta_buttons = []
        for idx, pta in enumerate(order):
            vis = get_visible_array_for_pta(idx)
            pta_buttons.append(dict(
                label = format_button_name(pta),
                method = "update",
                args = [
                    {"visible": vis},
                    {"title": f"Все быки для {pta}",
                    "xaxis.range": [None, None],
                    "yaxis.range": [None, None]}
                ]
            ))

        bull_buttons = []
        for bull_index, bull in enumerate(top_5_bulls):
            vis = get_visible_array_for_bull(current_pta_index, bull_index)
            bull_buttons.append(dict(
                label = format_button_name(bull.registered_name),
                method = "update",
                args = [
                    {"visible": vis},
                    {"title": f"{bull.registered_name} для {order[current_pta_index]}",
                    "xaxis.range": [None, None],
                    "yaxis.range": [None, None]},
                    # {"xaxis.title": f"{bull.registered_name} score"}
                ]
            ))

        # radar_trace = go.Scatterpolar(
        #     # r=avg_values,
        #     # theta=order,
        #     # fill='toself',
        #     # name='Average Cows',
        #     # line=dict(color='blue', width=4),
        #     # opacity=0.9,
        #     visible=False  # по умолчанию скрыт
        # )
        # fig.add_trace(radar_trace)

        fig.update_layout(
            # title="Распределение значений F(cow) для топ-5 быков (KDE)",
            # xaxis_title="PTA",
            yaxis_title="Density",
            showlegend=False,
            width=1100,
            margin=dict(l=50, r=300, t=50, b=50),
            plot_bgcolor='rgba(255, 255, 255, 0.8)',
            updatemenus=[
                {
                    "type": "buttons",
                    "direction": "down",
                    "x": 1.22,
                    "y": 1,
                    "xanchor": "left",
                    "yanchor": "top",
                    "showactive": True,
                    "buttons": bull_buttons
                },
                {
                    "type": "buttons",
                    "direction": "down",
                    "x": 1.01,
                    "y": 1,
                    "xanchor": "left",
                    "yanchor": "top",
                    "showactive": True,
                    "buttons": pta_buttons
                }
            ],
            xaxis=dict(
                domain=[0.05, 1],
            ),
            yaxis=dict(
                domain=[0, 1],
            )
        )

        config = {
            "scrollZoom": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["zoom", "zoomIn", "zoomOut", "autoScale", "toImage", "pan2d"]
        }

        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0, 0, 0, 0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0, 0, 0, 0.2)')
        fig.update_traces(hoverinfo='skip')


        fig.update_layout(dragmode='pan')
        fig_html = fig.to_html(full_html=False, config=config)
        return render(request, 'myapp/result.html', {'fig': fig_html})

    except Bull.DoesNotExist:
        messages.error(request, "Выбранные быки не найдены в базе данных")
        return redirect('pick_bulls')
    except Exception as e:
        messages.error(request, f"Ошибка при построении графиков: {str(e)}")
        return redirect('pick_bulls')


def sort_bulls(request):
    if request.method == "POST":
        form = BullSortForm(request.POST)
        print("Данные формы:", form.data)
        if form.is_valid():
            order = str(form['phenotype_order'])
            thresholds = str(form['thresholds']).replace("&quot;", "")

            l_index = order.find('value="') + len('value="')
            r_index = order.find('"', l_index)
            order = order[l_index:r_index].split('&quot;')[1::2]
            print(f"Selected order: {order}")

            l_index = thresholds.find('value="[') + len('value="[')
            r_index = thresholds.find(']"', l_index)
            thresholds = thresholds[l_index:r_index].split(',')

            for i in range(len(thresholds)):
                if thresholds[i] == 'None': thresholds[i] = None
                else: thresholds[i] = int(thresholds[i])

            print(f"Selected thresholds: {thresholds}")

            request.session.update({
                'original_order': order,
                'selected_bulls': [],
                'current_pareto': []
            })
            return redirect('pick_bulls')
    
    form = BullSortForm()
    missing_counts = request.session.get('missing_counts', {})
    return render(request, 'myapp/sort_form.html', {'form': form, 'missing_counts': missing_counts})


def auto_pairing(request):
    if 'uploaded_cows' not in request.session or not request.session['uploaded_cows']:
        messages.warning(request, "Сначала загрузите CSV файл с данными коров.")
        return redirect('upload')

    MIN_PER_BULL = 5
    MAX_PER_BULL = 10

    if request.method == "POST":
        num_cows = int(request.POST.get('num_cows', 0))
        budget = int(request.POST.get('budget', 0))
        
        MAX_COWS_LIMIT = 200
        if num_cows > MAX_COWS_LIMIT:
            messages.warning(request, f"Количество коров ограничено до {MAX_COWS_LIMIT} для оптимизации производительности.")
            num_cows = MAX_COWS_LIMIT
        
        try:
            uploaded_cows = request.session.get('uploaded_cows', {})
            # print(f"Загружено коров из сессии: {len(uploaded_cows)}")
            
            valid_cows_ancestors_list = []
            for cow_id, ancestors_ids in uploaded_cows.items():
                try:
                    father = Bull.objects.get(identification_number=ancestors_ids['bull_id'])
                    mgf = Bull.objects.get(identification_number=ancestors_ids['maternal_grandfather_id'])
                    ggf = Bull.objects.get(identification_number=ancestors_ids['great_grandfather_id'])
                    
                    valid_cows_ancestors_list.append({
                        'cow_id': cow_id,
                        'father': father,
                        'mgf': mgf,
                        'ggf': ggf
                    })
                except Bull.DoesNotExist:
                    continue

            print(f"Найдено коров с полными данными: {len(valid_cows_ancestors_list)}")

            if not valid_cows_ancestors_list:
                messages.error(request, "Не найдено коров с полными данными о предках.")
                return render(request, 'myapp/auto_pairing.html')

            all_bulls_qs = Bull.objects.all()
            
            assignments, net_profit = matcher.run_optimal_pairing(
                all_bulls_qs=all_bulls_qs,
                valid_cows_ancestors=valid_cows_ancestors_list,
                N_target=num_cows,
                B_budget=budget
            )

            print(f"Получено разбиений: {len(assignments)}")
            print(f"Общая прибыль: {net_profit}")

            request.session['pairing_results'] = {
                'assignments': [(a['cow_id'], a['bull'].registered_name, a['profit']) for a in assignments],
                'net_profit': net_profit
            }

            context = {
                'assignments': assignments,
                'net_profit': net_profit,
                'num_bulls_used': len(set(a['bull'].id for a in assignments)),
                'num_pairs': len(assignments),
                'num_cows': num_cows,
                'budget': budget
            }
            print("Подготовлен контекст для шаблона:", context)
            return render(request, 'myapp/auto_pairing.html', context)

        except Exception as e:
            print(f"Ошибка при выполнении алгоритма: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f"Ошибка при выполнении алгоритма: {str(e)}")
            return render(request, 'myapp/auto_pairing.html', {'num_cows': num_cows, 'budget': budget})

    return render(request, 'myapp/auto_pairing.html')


def download_pairing(request):
    results = request.session.get('pairing_results')
    if not results:
        messages.error(request, "Результаты разбиения не найдены")
        return redirect('auto_pairing')

    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="pairing_results.txt"'

    response.write('=' * 80 + '\n')
    response.write(f"{'РЕЗУЛЬТАТЫ АВТОМАТИЧЕСКОГО РАЗБИЕНИЯ':^80}\n")
    response.write('=' * 80 + '\n\n')

    response.write(f"Общая прибыль: {results['net_profit']}\n")
    response.write('-' * 80 + '\n\n')

    cow_col_width = 20
    bull_col_width = 40
    profit_col_width = 15

    header = (
        f"{'КОРОВА':<{cow_col_width}} | "
        f"{'БЫК':<{bull_col_width}} | "
        f"{'ПРИБЫЛЬ':>{profit_col_width}}\n"
    )
    response.write(header)
    response.write('-' * (cow_col_width + bull_col_width + profit_col_width + 4) + '\n')

    for cow_id, bull_name, profit in results['assignments']:
        row = (
            f"{str(cow_id):<{cow_col_width}} | "
            f"{str(bull_name):<{bull_col_width}} | "
            f"{str(profit):>{profit_col_width}}\n"
        )
        response.write(row)

    response.write('\n' + '=' * 80 + '\n')
    response.write(f"{'КОНЕЦ ОТЧЕТА':^80}\n")
    response.write('=' * 80 + '\n')

    return response


def reset_priorities(request):
    if 'original_order' in request.session:
        del request.session['original_order']
    if 'selected_bulls' in request.session:
        del request.session['selected_bulls']
    if 'current_pareto' in request.session:
        del request.session['current_pareto']
    request.session.modified = True
    
    # messages.info(request, "Приоритеты были сброшены.")
    return redirect('sort_bulls')