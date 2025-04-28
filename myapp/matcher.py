import heapq
import time
import sys
import random
import numpy as np
from operator import itemgetter
from collections import defaultdict

# Net Merit indexes
ECONOMIC_WEIGHTS_S = {
    'pta_milk': 3.2,
    'pta_fat': 31.8,
    'pta_protein': 13.0,
    'pta_productive_life': 13.0,
    'pta_scs': -2.6,
    'pta_dpr': 2.1,
    'pta_hcr': 0.5,
    'pta_ccr': 1.8,
    'pta_gestation_length': 0.0,
    'pta_milk_fever': 0.0,
    'pta_displaced_abomasum': 0.0,
    'pta_ketosis': 0.0,
    'pta_mastitis': 0.0,
    'pta_metritis': 0.0,
    'pta_retained_placenta': 0.0,
    'pta_early_first_calving': 1.0,
    'pta_heifer_livability': 0.8,
    'pta_feed_saved': 0.0,
    'pta_residual_feed_intake': -6.8
}

COST_PER_BULL_O = 50.0
PTA_KEYS = list(ECONOMIC_WEIGHTS_S.keys())

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total: 
        sys.stdout.write('\n')
        sys.stdout.flush()

def calculate_calf_pta_vector(bull, father, mgf, ggf):
    calf_pta = {}
    try:
        for key in PTA_KEYS:
            bull_val = getattr(bull, key, 0) or 0
            f_val = getattr(father, key, 0) or 0
            mgf_val = getattr(mgf, key, 0) or 0
            ggf_val = getattr(ggf, key, 0) or 0
            calf_pta[key] = (0.5 * bull_val + 0.25 * f_val + 0.125 * mgf_val + 0.0625 * ggf_val)
    except TypeError:
        print(f"Warning: TypeError calculating PTA for bull {bull.id}. Skipping.")
        return None
    return calf_pta

def calculate_gross_profit(calf_pta_vector, S):
    if calf_pta_vector is None:
        return -float('inf')
    profit = 0.0
    for trait, weight in S.items():
        profit += calf_pta_vector.get(trait, 0) * weight
    return profit

def select_candidate_bulls(all_bulls_qs, S, pool_size):
    start_time = time.time()
    num_all_bulls = all_bulls_qs.count()
    actual_pool_size = min(pool_size, num_all_bulls)
    print(f"Отбор {actual_pool_size} кандидатов из {num_all_bulls} быков...")
    
    if num_all_bulls > 20000:
        print("  Слишком много быков, используем случайную выборку для предварительного отбора...")
        sample_size = 20000
        sample_ids = random.sample(list(all_bulls_qs.values_list('id', flat=True)), min(sample_size, num_all_bulls))
        bull_data = all_bulls_qs.filter(id__in=sample_ids).values('id', *PTA_KEYS)
    else:
        bull_data = all_bulls_qs.values('id', *PTA_KEYS)
    
    print(f"  Расчет экономических оценок для {len(bull_data)} быков...")
    print_progress_bar(0, len(bull_data), prefix='Расчет оценок:', suffix='Завершено', length=50)
    
    scores = []
    processed = 0
    batch_size = 1000
    
    for i in range(0, len(bull_data), batch_size):
        batch = bull_data[i:i+batch_size]
        batch_scores = []
        
        for bd in batch:
            score = 0.0
            valid_score = True
            try:
                for trait, weight in S.items():
                    value = bd.get(trait) or 0 
                    score += value * weight
                batch_scores.append({'id': bd['id'], 'score': score})
            except (TypeError, ValueError) as e:
                continue
                
        scores.extend(batch_scores)
        processed += len(batch)
        print_progress_bar(processed, len(bull_data), prefix='Расчет оценок:', suffix='Завершено', length=50)
            
    print("\nСортировка быков по оценке...")
    scores.sort(key=itemgetter('score'), reverse=True)
    top_ids = [item['id'] for item in scores[:actual_pool_size]]
    
    candidates = list(all_bulls_qs.filter(id__in=top_ids))
    print(f"  Отобрано {len(candidates)} кандидатов за {time.time() - start_time:.2f} сек.")
    return candidates

def calculate_potential_assignments_optimized(candidate_bulls, valid_cows_ancestors, S, max_bulls_per_cow=50):
    start_time = time.time()
    num_bulls = len(candidate_bulls)
    num_cows = len(valid_cows_ancestors)
    
    print(f"Оптимизированный расчет потенциальных назначений для {num_cows} коров...")
    
    bull_scores = []
    for bull in candidate_bulls:
        score = 0.0
        for trait, weight in S.items():
            score += (getattr(bull, trait, 0) or 0) * weight
        bull_scores.append((bull, score))
    
    bull_scores.sort(key=itemgetter(1), reverse=True)
    
    max_bulls = min(max_bulls_per_cow, num_bulls)
    
    cow_batches = []
    batch_size = min(100, num_cows)
    for i in range(0, num_cows, batch_size):
        cow_batches.append(valid_cows_ancestors[i:i+batch_size])
    
    total_assignments = 0
    assignments = []
    
    for batch_idx, cow_batch in enumerate(cow_batches):
        print(f"  Обработка партии коров {batch_idx+1}/{len(cow_batches)} (размер: {len(cow_batch)})...")
        batch_assignments = []
        
        processed_count = 0
        total_in_batch = len(cow_batch) * max_bulls
        print_progress_bar(0, total_in_batch, prefix='Прогресс:', suffix='Завершено', length=50)
        
        for cow_idx, cow in enumerate(cow_batch):
            cow_assignments = []
            
            for bull_idx, (bull, _) in enumerate(bull_scores[:max_bulls]):
                calf_pta = calculate_calf_pta_vector(bull, cow['father'], cow['mgf'], cow['ggf'])
                if calf_pta is None:
                    processed_count += 1
                    continue
                
                profit = calculate_gross_profit(calf_pta, S)
                if profit != -float('inf'):
                    cow_assignments.append({'bull': bull, 'cow_id': cow['cow_id'], 'profit': profit})
                
                processed_count += 1
                if processed_count % 10 == 0 or processed_count == total_in_batch:
                    print_progress_bar(processed_count, total_in_batch, prefix='Прогресс:', suffix='Завершено', length=50)
            
            cow_assignments.sort(key=itemgetter('profit'), reverse=True)
            batch_assignments.extend(cow_assignments[:10])
        
        assignments.extend(batch_assignments)
        total_assignments += len(batch_assignments)
    
    print(f"\n  Рассчитано {total_assignments} валидных назначений за {time.time() - start_time:.2f} сек.")
    print(f"  Итоговое число назначений: {len(assignments)}")
    return assignments

def execute_greedy_heap_selection(potential_assignments, N_target, B_budget, o):
    start = time.time()
    max_assignments_per_bull = 5
    print(f"Запуск жадного алгоритма: N={N_target}, B={B_budget}, Стоимость быка={o}, Макс. назначений на быка (K)={max_assignments_per_bull}")
    
    cow_map = defaultdict(list)
    for pa in potential_assignments:
        if isinstance(pa['profit'], (int, float)):
            cow_map[pa['cow_id']].append(pa)
        else:
             print(f"Warning: Invalid profit type for cow {pa['cow_id']} bull {pa['bull'].id}. Skipping assignment.")
             
    for cid in cow_map:
        cow_map[cid].sort(key=itemgetter('profit'), reverse=True)

    heap = []
    pointers = {}
    for cid, assigns in cow_map.items():
        if assigns:
            best = assigns[0]
            mnp = best['profit'] - o 
            heapq.heappush(heap, (-mnp, best['profit'], best['bull'].id, cid, best['bull']))
            pointers[cid] = 0
        else:
             print(f"Warning: No valid assignments found for cow {cid} after filtering.")

    print(f"  Начальный размер кучи: {len(heap)}")
    
    result = []
    used_bulls = set()
    assigned_cows = set()
    assignments_per_bull = defaultdict(int)
    total_gross = 0.0
    total_cost = 0.0

    print_progress_bar(0, N_target, prefix='Выбор пар:', suffix=f'0/{N_target}', length=50)
    
    while heap and len(result) < N_target:
        neg_mnp, profit, bid, cid, bull = heapq.heappop(heap)
        
        skip_assignment = False
        reason = ""
        
        if cid in assigned_cows:
            skip_assignment = True
            reason = "Корова уже назначена"
        elif assignments_per_bull.get(bid, 0) >= max_assignments_per_bull:
            skip_assignment = True
            reason = f"Достигнут лимит ({max_assignments_per_bull}) для быка {bid}"
        else:
            marginal_cost = o if bid not in used_bulls else 0
            if total_cost + marginal_cost > B_budget:
                skip_assignment = True
                reason = f"Бюджет ({B_budget}) превышен (нужно {total_cost + marginal_cost})"

        if not skip_assignment:
            assigned_cows.add(cid)
            assignments_per_bull[bid] = assignments_per_bull.get(bid, 0) + 1
            total_gross += profit
            
            if bid not in used_bulls:
                used_bulls.add(bid)
                total_cost += o
                
            result.append({'bull': bull, 'cow_id': cid, 'profit': profit})
            print_progress_bar(len(result), N_target, prefix='Выбор пар:', suffix=f'{len(result)}/{N_target}', length=50)
        else:
            idx = pointers[cid] + 1
            pointers[cid] = idx
            
            if idx < len(cow_map[cid]):
                nxt = cow_map[cid][idx]
                cost_for_next = o if nxt['bull'].id not in used_bulls else 0
                mnp_next = nxt['profit'] - cost_for_next
                heapq.heappush(heap, (-mnp_next, nxt['profit'], nxt['bull'].id, cid, nxt['bull']))

    net_profit = total_gross - total_cost
    print(f"\n  Завершено за {time.time() - start:.2f} сек. Назначено={len(result)}, Использовано быков={len(used_bulls)}")
    print(f"  Валовая прибыль={total_gross:.2f}, Затраты={total_cost:.2f}, Чистая прибыль={net_profit:.2f}")
    
    print("  Топ-10 использованных быков:")
    for bull_id, count in sorted(assignments_per_bull.items(), key=lambda item: item[1], reverse=True)[:10]:
        print(f"    Бык {bull_id}: {count} назначений")
        
    result.sort(key=itemgetter('profit'), reverse=True)
    return result, net_profit

def run_optimal_pairing(all_bulls_qs, valid_cows_ancestors, N_target, B_budget, u_candidate_pool_size=1000):
    print("--- Запуск оптимального подбора --- ")
    
    if not valid_cows_ancestors:
        print("Ошибка: Список коров для подбора пуст.")
        return [], 0.0
    
    num_cows = len(valid_cows_ancestors)
    if num_cows > 1000:
        u_candidate_pool_size = min(u_candidate_pool_size, 1000)
        print(f"Большое количество коров ({num_cows}), уменьшаем пул кандидатов до {u_candidate_pool_size}")
    
    candidates = select_candidate_bulls(all_bulls_qs, ECONOMIC_WEIGHTS_S, u_candidate_pool_size)
    if not candidates:
        print("Ошибка: Не удалось отобрать быков-кандидатов.")
        return [], 0.0
        
    max_bulls_per_cow = 50 if num_cows <= 500 else 30 if num_cows <= 1000 else 15
    print(f"Используем {max_bulls_per_cow} быков на корову для оптимизации")
    
    potential = calculate_potential_assignments_optimized(
        candidates, 
        valid_cows_ancestors, 
        ECONOMIC_WEIGHTS_S,
        max_bulls_per_cow=max_bulls_per_cow
    )
    
    if not potential:
        print("Ошибка: Не удалось рассчитать потенциальные назначения.")
        return [], 0.0
        
    assignments, net_profit = execute_greedy_heap_selection(potential, N_target, B_budget, COST_PER_BULL_O)
    print("--- Оптимальный подбор завершен --- ")
    return assignments, net_profit
