import numpy as np
from .models import Bull

try:
    from pymoo.util.nds.efficient_non_dominated_sort import efficient_non_dominated_sort
    PYMOO_AVAILABLE = True
    print("pymoo library found. Using optimized Pareto calculation.")
except ImportError:
    PYMOO_AVAILABLE = False
    print("WARNING: pymoo library not found. Falling back to slow Pareto calculation.")

NEGATIVE_TRAITS = {
    'pta_scs', 'pta_residual_feed_intake', 
    'pta_milk_fever', 'pta_displaced_abomasum',
    'pta_ketosis', 'pta_mastitis', 'pta_metritis',
    'pta_retained_placenta', 'pta_gestation_length'
}

def find_pareto_front_slow(bulls_list, traits):
    if not bulls_list:
        return []
    
    pareto_front_indices = set(range(len(bulls_list))) 

    for i, candidate_bull in enumerate(bulls_list):
        if i not in pareto_front_indices:
            continue
            
        for j, comparison_bull in enumerate(bulls_list):
            if i == j or j not in pareto_front_indices:
                continue

            comparison_dominates_candidate = True
            comparison_is_strictly_better_in_one = False

            for trait in traits:
                candidate_val = getattr(candidate_bull, trait, None)
                comparison_val = getattr(comparison_bull, trait, None)

                if candidate_val is None or comparison_val is None:
                    comparison_dominates_candidate = False
                    break 
                    
                is_negative = trait in NEGATIVE_TRAITS

                if (is_negative and comparison_val > candidate_val) or \
                   (not is_negative and comparison_val < candidate_val):
                    comparison_dominates_candidate = False
                    break 
                
                if (is_negative and comparison_val < candidate_val) or \
                   (not is_negative and comparison_val > candidate_val):
                    comparison_is_strictly_better_in_one = True

            if comparison_dominates_candidate and comparison_is_strictly_better_in_one:
                pareto_front_indices.discard(i)
                break 

    final_pareto_front_objects = [bulls_list[i] for i in pareto_front_indices]
    final_pareto_front_ids = [b.id for b in final_pareto_front_objects]

    if final_pareto_front_objects and traits:
         is_negative_sort = traits[0] in NEGATIVE_TRAITS
         final_pareto_front_objects.sort(
             key=lambda b: getattr(b, traits[0], -np.inf if not is_negative_sort else np.inf),
             reverse=not is_negative_sort)
         final_pareto_front_ids = [b.id for b in final_pareto_front_objects]

    return final_pareto_front_ids

def find_pareto_front_optimized(ids, F_values, traits):
    if F_values.size == 0 or len(ids) != F_values.shape[0]:
        print("Invalid input for optimized Pareto calculation.")
        return []

    n_traits = F_values.shape[1]
    if n_traits != len(traits):
         print("Mismatch between traits length and data columns in optimized function.")
         return []

    F_minimized = np.copy(F_values)
    for j, trait in enumerate(traits):
         if trait not in NEGATIVE_TRAITS:
             mask_not_nan = ~np.isnan(F_minimized[:, j])
             F_minimized[mask_not_nan, j] = -F_minimized[mask_not_nan, j]
             
    mask_valid = np.all(~np.isnan(F_minimized), axis=1)
    valid_row_indices = np.where(mask_valid)[0] 

    if len(valid_row_indices) == 0:
        print("No bulls with complete data for selected traits found.")
        return [] 
        
    F_valid = F_minimized[valid_row_indices, :]
    ids_valid = ids[valid_row_indices]
    
    try:
        fronts = efficient_non_dominated_sort(F_valid) 
    except Exception as e:
        print(f"Error during efficient_non_dominated_sort: {e}")
        return [] 

    if not fronts: 
        return []
        
    nd_indices_relative_to_valid = fronts[0]

    pareto_bull_ids = ids_valid[nd_indices_relative_to_valid].tolist()

    if pareto_bull_ids and traits:
        try:
            sort_trait_index = traits.index(traits[0])
            is_negative_sort = traits[0] in NEGATIVE_TRAITS
            
            pareto_values_for_sort = F_valid[nd_indices_relative_to_valid, sort_trait_index]
            
            id_value_pairs = list(zip(pareto_bull_ids, pareto_values_for_sort))
            
            id_value_pairs.sort(key=lambda x: x[1], reverse=is_negative_sort)
            
            pareto_bull_ids = [pair[0] for pair in id_value_pairs]
        except IndexError:
            pass
        except Exception as e:
            print(f"Error during optional sorting of Pareto IDs: {e}")

    return pareto_bull_ids


def find_pareto_front(all_bull_data, traits):
    if not traits or not all_bull_data:
        return [data[0] for data in all_bull_data]

    if PYMOO_AVAILABLE:
        try:
            raw_array = np.array(all_bull_data, dtype=object)
            ids = raw_array[:, 0].astype(int)
            F_raw = raw_array[:, 1:].astype(str)
            F_raw[F_raw == 'None'] = np.nan
            F_values = F_raw.astype(float)
            return find_pareto_front_optimized(ids, F_values, traits)
        except Exception as e:
            print(f"Error preparing data for pymoo, falling back to slow method: {e}")
            ids_to_fetch = [data[0] for data in all_bull_data]
            bull_objects = list(Bull.objects.filter(id__in=ids_to_fetch))
            return find_pareto_front_slow(bull_objects, traits)
    else:
        ids_to_fetch = [data[0] for data in all_bull_data]
        bull_objects = list(Bull.objects.filter(id__in=ids_to_fetch))
        return find_pareto_front_slow(bull_objects, traits)
