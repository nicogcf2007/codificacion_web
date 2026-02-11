"""
Core logic module - Extracted from ui.py
Contains all business logic for survey coding with AI
"""
import os
import pandas as pd
import re
import time
from openai import OpenAI
from typing import Callable, Optional, Tuple, Set, Dict, List, Any

# Import API key from config
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import openai_api_key_Codifiacion

# Configure OpenAI API
client = OpenAI(api_key=openai_api_key_Codifiacion)

# Global variables
PROCESS_STOPPED = False
MODIFIED_CELLS: Set[Tuple[int, str]] = set()
questions_dict: Dict[str, Set[Tuple[str, str]]] = {}


def load_files(responses_path: str, codes_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load Excel files for responses and codes"""
    responses_df = pd.read_excel(responses_path)
    codes_df = pd.read_excel(codes_path, sheet_name='Codificación')
    codes_df.columns = codes_df.columns.str.strip()
    return responses_df, codes_df


def select_columns(codes_df: pd.DataFrame, question_column: str) -> pd.DataFrame:
    """Select and prepare columns from codes dataframe"""
    codes_df[question_column] = codes_df[question_column].ffill()
    selected_questions = codes_df[[question_column, 'Label', 'Id campo', 'Cod']]
    return selected_questions


def request_openai(messages: List[Dict[str, str]], max_retries: int = 5, 
                   stop_requested_check: Optional[Callable] = None) -> Optional[Any]:
    """Make request to OpenAI API with retry logic"""
    global PROCESS_STOPPED
    
    for attempt in range(max_retries):
        if PROCESS_STOPPED or (stop_requested_check and stop_requested_check()):
            print("Solicitud a OpenAI cancelada - proceso detenido")
            return None
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_completion_tokens=400
            )
            
            print(f"\n[OpenAI Logic] Solicitud exitosa (Intento {attempt + 1})")
            print("="*50)
            print(f"[OpenAI Logic] Response Object: {response}")
            print(f"[OpenAI Logic] Content: {response.choices[0].message.content}")
            print("="*50)
            
            return response
        except Exception as e:
            print(f"Error en la solicitud a OpenAI: {e}. Intento {attempt + 1} de {max_retries}.")
            
            if stop_requested_check and stop_requested_check():
                print("Solicitud a OpenAI cancelada durante reintento")
                return None
                
            if attempt < max_retries - 1:
                time.sleep(10)
            else:
                raise


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def filter_exclusive_codes(assigned_codes_list: List[str]) -> List[str]:
    """Filter exclusive codes from assigned codes list"""
    exclusive_codes = {'66', '77', '88', '99', '777', '888', '999'}
    non_exclusive_codes = [code for code in assigned_codes_list if code not in exclusive_codes]
    
    if non_exclusive_codes:
        return non_exclusive_codes
    elif assigned_codes_list:
        return [assigned_codes_list[0]]
    else:
        return []


def get_next_valid_code(existing_codes: pd.Series) -> str:
    """Get next valid code, excluding reserved codes"""
    valid_codes = [int(code) for code in existing_codes if int(code) not in {66, 77, 88, 99, 777, 888, 999}]
    next_code = max(valid_codes, default=0) + 1
    while next_code in {66, 77, 88, 99, 777, 888, 999}:
        next_code += 1
    return f"{next_code:02}"


def assign_labels_to_response(question: str, response: str, labels: List[str], 
                              codes: List[str], is_single_response: bool = False,
                              stop_requested_check: Optional[Callable] = None,
                              max_labels: int = 6,
                              context: str = "") -> str:
    """Assign labels to a survey response using AI"""
    labels_str = ', '.join([f"{label} (code: {code})" for label, code in zip(labels, codes)])
    
    context_instruction = ""
    if context:
        context_instruction = f"CONTEXTO ADICIONAL SOBRE LA PREGUNTA: {context}\nUsa este contexto para entender mejor el significado de las respuestas."

    messages = [
        {"role": "system", 
         "content": "You are an expert in coding survey responses with a focus on both 'thematic match' and 'conceptual match.' Assign codes accurately, concisely, and strictly based on the provided instructions without additional comments."},
        {"role": "user", 
         "content": f"""The question is: {question}
         {context_instruction}
         The response is: {response}
         The available codes are: {labels_str}
         VERY IMPORTANT:
         ALWAYS check existing labels first and reuse them if they match conceptually and thematic match.
         Instructions:
         Si hay varios codigos repetidos o con ideas similares que se puedan usar en una respuesta solo usa uno no los uses todos en una respuesta, usa el que más se ajuste textualmente.
         Si la respuesta no es coherente a la pregunta asigna 99
         If no existing code fits the response, reply with 'NEW_LABEL_NEEDED' instead of assigning any code.
         1. Assign only the codes that fit the response based on thematic or conceptual alignment.Not use codes 66, 77, 88, and 99.
         2. Only if in {labels_str} there are no labels or codes other than codes 66, 77, 88, 99 respond with 'NEW_LABEL_NEEDED'
         3. Be conservative in code assignment - it's better to assign fewer, highly relevant codes than too many.
         4. Using codes 66, 77, 88, and 99 unless strictly necessary.
         5. Do not combine codes 66, 77, 88, or 99 with other codes or with each other.
         6. Provide only the numeric codes in your response, separated by semicolons if multiple codes are assigned.
         7. Do not assign more than {max_labels} codes per answer.
         9. If the answer is not logical text and is just signs or symbols, assign code 99.
         10. Assign only one code if this is a single response question.
         """}
    ]
    
    response_obj = request_openai(messages, stop_requested_check=stop_requested_check)
    
    if response_obj is None:
        return "77"
        
    assigned_codes = response_obj.choices[0].message.content.strip()
    if is_single_response:
        assigned_codes = assigned_codes.split(';')[0].strip()
    return assigned_codes


def create_new_labels(question: str, response: str, available_labels: List[str],
                     available_codes: List[str], codes_df: pd.DataFrame,
                     stop_requested_check: Optional[Callable] = None) -> Optional[str]:
    """Create new label for a response using AI"""
    response_str = str(response).strip().lower()

    all_existing_labels = list(available_labels) + list(codes_df.loc[codes_df['Nombre de la Pregunta'] == question, 'Label'].str.lower())
    normalized_labels = [normalize_text(label) for label in all_existing_labels]

    normalized_response = normalize_text(response_str)
    if normalized_response in normalized_labels:
        index_in_labels = normalized_labels.index(normalized_response)
        if index_in_labels < len(available_labels):
            print(f"Etiqueta existente encontrada para '{response_str}', reutilizando la etiqueta.")
            return available_labels[index_in_labels]
    
    messages = [
        {"role": "system", "content": """You are an expert in coding survey responses.
        Your task is to either reuse an existing label or create a new one that can be reused for similar responses.
        
        Antes de generar una etiqueta asegurate de que esa idea se repite al menos 3 veces en mas respuestas. 
        
        VERY IMPORTANT:
        Recuerda que las etiquetas creadas deben estar en español latinoamericano (Colombiano)
        The new labels created must be with perfect spelling.
        ALWAYS check existing labels first and reuse them if they match conceptually
        
        If the answer is a name of a television show, series or movie, first make sure that the television show, series or movie actually exists and second, if you must create the tag, create it with the name correctly written as the response may have errors spelling 
        
        Don't forget to first check the existing tags so as not to create repeated tags written in different ways, for example "Betty la Fea" and "bety la fea"
        
        Rules for label creation/selection:
        1. ALWAYS check existing labels first and reuse them if they match conceptually. Do not use codes 66, 77, 777, 88, 888, 99, 999.
        2. Labels must be short (4-6 words maximum).
        3. Use general categories that can be applied to multiple responses.
        4. Standardize similar concepts under a single label.
        5. Return only the label, no explanations.
        6. Do not create an "Otro" or "Otros" tag.
        """},
        {"role": "user", "content": f"""
        Question: {question}
        Response to code: {response_str}
        
        Current available labels: {available_labels}
        
        Instructions:
        1. The label must have excellent spelling.
        2. Check if the response matches ANY existing label conceptually.
        3. If yes, return that label.
        4. If no, create a new general label that can be reused.
        5. Return only the label text, no explanations. 
        6. No response can be left without an assigned code.
        """}
    ]
    
    response_obj = request_openai(messages, stop_requested_check=stop_requested_check)
    
    if response_obj is None:
        return None
        
    result = response_obj.choices[0].message.content.strip()

    if result and not any(char in result for char in "()") and normalize_text(result) not in normalized_labels:
        print(f"Nueva etiqueta generada: {result}")
        return result
    else:
        print(f"Advertencia: Formato inesperado o etiqueta duplicada para la nueva etiqueta: {result}")
        return None


def save_new_label(codes_df: pd.DataFrame, question: str, label: str, new_code: str) -> Tuple[pd.DataFrame, bool]:
    """Save a new label to the codes dataframe"""
    question_row = codes_df.loc[codes_df['Nombre de la Pregunta'] == question]
    # print(f"question_row: {question_row}")
    
    if question_row.empty:
        print(f"Warning: Question '{question}' not found in codes_df. Cannot save new label.")
        return codes_df, False
    
    id_campo = question_row['Id campo'].iloc[0]
    form_question = question_row['# Pregunta del formulario'].iloc[0]
    
    new_row = pd.DataFrame({
        'Id campo': [id_campo],
        'Cod': [new_code],
        'Label': [label],
        'Agrupación': [None],
        '# Pregunta del formulario': [form_question],
        'Nombre de la Pregunta': [question]
    })
    
    codes_df = pd.concat([codes_df, new_row], ignore_index=True)
    print(f"Nueva etiqueta guardada: {label} con código {new_code} para la pregunta '{question}'")
    
    return codes_df, True


def process_response(question: str, response: str, available_labels: List[str],
                    available_codes: List[str], limit_77: Dict, limit_labels: Dict,
                    codes_df: pd.DataFrame, stop_requested_check: Optional[Callable] = None,
                    max_labels: int = 6, context: str = "") -> Tuple[str, pd.DataFrame]:
    """Process a single response and assign codes"""
    global questions_dict
    
    response_str = str(response).strip().lower()
    is_single_response = '(respuesta única)' in question or max_labels == 1

    excluded_codes = {'66', '77', '88', '99', '777', '888', '999'}
    filtered_labels_codes = [
        (label, code) for label, code in zip(available_labels, available_codes)
        if code not in excluded_codes
    ]
    filtered_labels, filtered_codes = zip(*filtered_labels_codes) if filtered_labels_codes else ([], [])

    # print(f"[Processing response for question '{question}']")

    assigned_codes = assign_labels_to_response(
        question, response_str, filtered_labels, filtered_codes, 
        is_single_response, stop_requested_check,
        max_labels=max_labels, context=context
    )
    
    if assigned_codes == "NEW_LABEL_NEEDED" or assigned_codes == "":
        print(f"Etiqueta nueva necesaria para la respuesta: '{response_str}'")

        # Check column limit of new labels
        # Note: If max is 0, this condition is true (count >= 0)
        if limit_labels['count'] >= limit_labels['max']:
            print(f"Límite de nuevas etiquetas para esta pregunta alcanzado ({limit_labels['count']}/{limit_labels['max']}). Asignando código 77.")
            assigned_codes = "77"
        else:
            new_label = create_new_labels(
                question, response_str, filtered_labels, filtered_codes, 
                codes_df, stop_requested_check
            )
            
            if new_label:
                # Verificar si la etiqueta ya existe en codes_df para esta pregunta (evitar duplicados)
                # Esto previene que se cree un nuevo código (ej: 11) si ya existe uno (ej: 10) para la misma etiqueta
                existing_entry = codes_df.loc[
                    (codes_df['Nombre de la Pregunta'] == question) & 
                    (codes_df['Label'].astype(str).str.lower() == new_label.lower()), 
                    'Cod'
                ]
                
                if not existing_entry.empty:
                    # Usar código existente
                    existing_code_val = existing_entry.iloc[0]
                    try:
                        assigned_codes = f"{int(existing_code_val):02d}"
                    except:
                        assigned_codes = str(existing_code_val)
                    # print(f"Reutilizando etiqueta existente '{new_label}' con código {assigned_codes}")
                else:
                    # Crear nuevo código si no existe
                    existing_codes = codes_df.loc[codes_df['Nombre de la Pregunta'] == question, 'Cod']
                    new_code = get_next_valid_code(existing_codes)
                    codes_df, label_created = save_new_label(codes_df, question, new_label, new_code)
                    
                    if label_created:
                        print(f"Nueva etiqueta creada: '{new_label}' con código {new_code}")

                        available_codes.append(new_code)
                        available_labels.append(new_label)

                        limit_labels['count'] += 1
                        limit_77['new_labels'].append((question, new_label, new_code))

                        if question in questions_dict:
                            questions_dict[question].add((new_code, new_label))
                        else:
                            questions_dict[question] = {(new_code, new_label)}
                        
                        assigned_codes = new_code
                    else:
                        print(f"No se pudo crear una nueva etiqueta para '{response_str}', asignando código 77")
                        assigned_codes = "77"
            else:
                print(f"No se generó una nueva etiqueta para '{response_str}', asignando código 77")
                assigned_codes = "77"
    else:
        # print(f"Etiqueta existente asignada: '{assigned_codes}' para la respuesta '{response_str}'")
        pass

    assigned_codes_list = re.findall(r'\d+', str(assigned_codes))
    assigned_codes_list = [f"{int(code):02d}" for code in assigned_codes_list]
    assigned_codes_list = list(set(assigned_codes_list))

    if is_single_response:
        assigned_codes_list = assigned_codes_list[:1]
        
    final_codes = ';'.join(assigned_codes_list)

    # print(f"Códigos asignados finales para la respuesta '{response_str}': {final_codes}")
    return final_codes, codes_df


def group_labels_codes(selected_questions: pd.DataFrame, response_columns: List[str]) -> Dict[str, Set[Tuple[str, str]]]:
    """Group labels and codes by question"""
    questions_dict = {}

    for _, row in selected_questions.iterrows():
        if pd.isna(row['Id campo']):
            continue
        
        id_campos = [campo.strip() for campo in row['Id campo'].split('-')]
        
        for col in response_columns:
            col_base = col[:-5] if col.endswith('_OTRO') or col.endswith('_OTRA') else f"C{col}"
            if any(col_base == id_campo for id_campo in id_campos):
                questions = row['Nombre de la Pregunta'].split(' / ')
                labels = str(row['Label']).split(',')
                codes = str(row['Cod']).split(',') if not pd.isna(row['Cod']) else []

                for question in questions:
                    if question not in questions_dict:
                        questions_dict[question] = set()
                    questions_dict[question].update(zip(codes, labels))
    
    # print(f"questions_dict {questions_dict}")
    
    return questions_dict


def process_responses(responses_df: pd.DataFrame, codes_df: pd.DataFrame, 
                     columns_config: List[Dict], question_column: str,
                     limit_77: Dict, limit_labels: Dict,
                     progress_callback: Optional[Callable] = None,
                     status_callback: Optional[Callable] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Process all responses and assign codes"""
    global PROCESS_STOPPED, MODIFIED_CELLS, questions_dict
    
    print("EJECUTANDO PROCESS_RESPONSES")
    
    # Extract column names from config
    response_columns = [col['name'] for col in columns_config]
    
    # Create a map for quick config lookup
    config_map = {col['name']: col for col in columns_config}
    
    selected_questions = select_columns(codes_df, question_column)
    questions_dict = group_labels_codes(selected_questions, response_columns)
    new_labels = []

    updated_codes_df = codes_df.copy()
    
    total_records = sum(len(responses_df[col].dropna().unique()) for col in response_columns)
    processed_records = 0

    def check_stop():
        global PROCESS_STOPPED
        return PROCESS_STOPPED

    column_to_questions = {}
    for _, row in selected_questions.iterrows():
        if pd.isna(row['Id campo']):
            continue
        
        id_campos = [campo.strip() for campo in row['Id campo'].split('-')]
        questions = row['Nombre de la Pregunta'].split(' / ')
        
        for col in response_columns:
            col_base = col[:-5] if col.endswith('_OTRO') or col.endswith('_OTRA') else f"C{col}"
            if any(col_base == id_campo for id_campo in id_campos):
                if col not in column_to_questions:
                    column_to_questions[col] = set()
                column_to_questions[col].update(questions)

    for i, col in enumerate(response_columns):
        if PROCESS_STOPPED:
            return responses_df, codes_df
            
        if status_callback:
            status_callback(f"Procesando columna {i + 1} de {len(response_columns)}: {col}")
        
        relevant_questions = column_to_questions.get(col, set())
        if not relevant_questions:
            print(f"⚠️ No se encontraron preguntas asociadas a la columna {col}. Omitiendo.")
            continue
            
        print(f"Preguntas relevantes para columna {col}: {relevant_questions}")
        
        if col.endswith('_OTRO') or col.endswith('_OTRA'):
            responses_df, updated_codes_df = process_other_columns(
                responses_df, [col], questions_dict, updated_codes_df,
                progress_callback, status_callback, total_records, check_stop
            )
        else:
            code_column = f'C{col}'
            if code_column not in responses_df.columns:
                responses_df[code_column] = ""

            responses_df[code_column] = responses_df[code_column].apply(
                lambda x: ';'.join([f"{int(cod):02}" for cod in str(x).split(';') if cod.strip().isdigit()]) if pd.notna(x) else ""
            )

            unique_responses = responses_df[col].dropna().unique()
            for j, response in enumerate(unique_responses):
                if PROCESS_STOPPED:
                    break
                    
                if j % max(1, len(unique_responses)//100) == 0 and status_callback:
                    status_callback(f"Procesando {col}: {j+1}/{len(unique_responses)}")
                
                # Check if this cell was already manually coded/processed
                # Note: This logic processes by unique response, so we need to be careful.
                # If unique response is "XYZ" and it was manually coded in apply_manual_coding,
                # then responses_df should already have the code in 'C{col}'.
                
                # We need to check if ALL instances of this response already have a code.
                # Since we update the dataframe in-place in process_response, 
                # we can check if the first instance of this response has a code.
                mask = responses_df[col] == response
                existing_codes_for_response = responses_df.loc[mask, code_column].unique()
                
                # If we have a valid code already (and it's not empty), skip AI processing
                # Assuming empty is "" or nan
                has_code = False
                for ec in existing_codes_for_response:
                    if pd.notna(ec) and str(ec).strip() != "":
                        has_code = True
                        break
                
                if has_code:
                    # Already coded (likely by manual process), just update progress and continue
                    processed_records += 1
                    if progress_callback:
                        progress_callback(processed_records / total_records)
                    continue

                for question in relevant_questions:
                    if question not in questions_dict:
                        continue
                        
                    data = questions_dict[question]
                    available_codes, available_labels = zip(*data)
                    available_labels = list(available_labels)
                    available_codes = list(available_codes)
                    
                    # Get specific config for this column
                    col_config = config_map.get(col, {})
                    max_labels = col_config.get('maxLabels', 6)
                    context = col_config.get('context', "")
                    
                    # New: Get per-column max new labels limit
                    # Default to 8 if not specified (legacy behavior), but frontend now sets it
                    # If 0, it means NO new labels allowed
                    col_max_new_labels = col_config.get('maxNewLabels', 8)
                    if col_max_new_labels is None: 
                        col_max_new_labels = 8 # Fallback
                    
                    # Create a specific limit object for this column processing
                    # We reuse 'limit_labels' structure but with column-specific max
                    # NOTE: 'count' here should track NEW labels created for THIS column.
                    # Since process_response increments the counter passed to it, we need a 
                    # way to persist this counter PER COLUMN across loop iterations.
                    # We can use a dictionary keyed by column name in the outer scope.
                    
                    # Initialize counter for this column if not exists
                    if 'col_counters' not in limit_labels:
                        limit_labels['col_counters'] = {}
                    
                    if col not in limit_labels['col_counters']:
                        limit_labels['col_counters'][col] = 0
                        
                    # Create a proxy limit object that process_response can update
                    # This is tricky because process_response expects a dict with 'count' and 'max'
                    # and increments 'count'. 
                    # We construct it on the fly.
                    
                    current_col_limit = {
                        'count': limit_labels['col_counters'][col],
                        'max': col_max_new_labels
                    }
                    
                    # If multi-label is false, force max_labels to 1
                    if not col_config.get('multiLabel', False):
                        max_labels = 1

                    assigned_codes, updated_codes_df = process_response(
                        question, response, available_labels, available_codes, 
                        limit_77, current_col_limit, updated_codes_df, check_stop,
                        max_labels=max_labels, context=context
                    )
                    
                    # Update the persistent counter with the new value
                    limit_labels['col_counters'][col] = current_col_limit['count']

                    responses_df.loc[mask, code_column] = assigned_codes
                    
                    modified_indices = responses_df.index[mask].tolist()
                    for idx in modified_indices:
                        MODIFIED_CELLS.add((idx, code_column))
                    
                    processed_records += 1
                    if progress_callback:
                        progress_callback(processed_records / total_records)
                    
                    break

    return responses_df, updated_codes_df


def process_other_columns(responses_df: pd.DataFrame, response_columns: List[str],
                         questions_dict: Dict, update_codes_df: pd.DataFrame,
                         progress_callback: Optional[Callable] = None,
                         status_callback: Optional[Callable] = None,
                         total_records: int = 0,
                         stop_requested: Optional[Callable] = None,
                         start_code: int = 501) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Process columns ending with _OTRO or _OTRA"""
    global MODIFIED_CELLS
    
    print("EJECUTANDO PROCESS_OTHER_COLUMNS")
    excluded_codes = {'66', '77', '88', '99', '00', '777', '888', '999'}
    new_labels = []
    processed_records = 0

    for col in response_columns:
        if stop_requested and stop_requested():
            return responses_df, update_codes_df
            
        if col.endswith('_OTRO') or col.endswith('_OTRA'):
            col_without_other = col[:-5]
            if col_without_other not in responses_df.columns:
                responses_df[col_without_other] = ""

            responses_df[col_without_other] = responses_df[col_without_other].apply(
                lambda x: ';'.join([f"{int(code):02d}" for code in str(x).split(';') if code.strip().isdigit()])
            )
            
            other_responses = responses_df[col]
            for idx, response in other_responses.items():
                if pd.isna(response):
                    continue

                for question, data in questions_dict.items():
                    if isinstance(data, set) and all(isinstance(item, tuple) and len(item) == 2 for item in data):
                        available_labels, available_codes = zip(*data)
                        available_labels = list(available_labels)
                        available_codes = list(available_codes)
                    else:
                        continue

                    assigned_codes, update_codes_df = process_response(
                        question, response,
                        available_labels, available_codes,
                        {'count': 0, 'max': start_code, 'new_code': 0, 'new_labels': new_labels},
                        {'count': 0, 'max': 8},
                        update_codes_df
                    )

                    current_codes = str(responses_df.at[idx, col_without_other]).strip()
                    current_codes_set = set(current_codes.split(';')) if current_codes else set()
                    new_codes_set = set(str(assigned_codes).split(';')) if assigned_codes else set()

                    new_codes_set = {f"{int(code):02d}" for code in new_codes_set}
                    current_codes_set = {f"{int(code):02d}" for code in current_codes_set}

                    combined_codes_set = current_codes_set | new_codes_set
                    non_excluded_codes = combined_codes_set - excluded_codes

                    if non_excluded_codes:
                        combined_codes_set = non_excluded_codes

                    if '77' in current_codes_set:
                        current_codes_set.remove('77')
                        replacement_codes = new_codes_set - current_codes_set
                        if replacement_codes:
                            replacement_codes_str = f"[{';'.join(sorted(replacement_codes))}]"
                            final_codes = ';'.join(sorted(current_codes_set)) + (f";{replacement_codes_str}" if current_codes_set else replacement_codes_str)
                        else:
                            final_codes = ';'.join(sorted(current_codes_set))
                    else:
                        final_codes = ';'.join(sorted(combined_codes_set))

                    final_codes_list = final_codes.split(';')
                    final_filtered_codes = [code for code in final_codes_list if code not in excluded_codes] or final_codes_list

                    responses_df.at[idx, col_without_other] = ';'.join(final_filtered_codes)
                    
                    MODIFIED_CELLS.add((idx, col_without_other))

                    processed_records += 1
                    if progress_callback:
                        progress_callback(processed_records / total_records)
                    if status_callback:
                        status_callback(f"Procesando registro {processed_records} de {total_records}")

    print(f"Nuevas etiquetas creadas: {new_labels}")
    print(f"update_codes_df antes del return en otros: {update_codes_df}")

    return responses_df, update_codes_df


def update_codes_file(codes_df: pd.DataFrame, new_labels: List[Tuple]) -> pd.DataFrame:
    """Update codes file with new labels"""
    excluded_codes = {66, 77, 88, 99, 0, 777, 888, 999}

    for id_campo, label, _ in new_labels:
        clean_label = re.sub(r'\(\d{3}\)', '', label).strip()
        # print(f"clean_label: {clean_label}")

        codes_df['Id campo'] = codes_df['Id campo'].astype(str).str.strip().str.upper()
        id_campo_normalized = str(id_campo).strip().upper()
        # print(f"id_campo_normalized: {id_campo_normalized}")

        question_rows = codes_df.loc[codes_df['Id campo'] == id_campo_normalized]
        # print(f"question_rows: {question_rows}")

        if question_rows.empty:
            print(f"Warning: Question with Id campo '{id_campo}' not found in DataFrame. Skipping update.")
            continue

        existing_codes_question = question_rows['Cod'].astype(int)
        # print(f"existing_codes_question: {existing_codes_question}")

        valid_codes = [cod for cod in existing_codes_question if cod not in excluded_codes]
        # print(f"valid_codes: {valid_codes}")

        new_code = max(valid_codes, default=0) + 1
        # print(f"new_code: {new_code}")

        form_question = question_rows['# Pregunta del formulario'].ffill().bfill().values[0]
        # print(f"form_question: {form_question}")

        new_row = pd.DataFrame({
            'Id campo': [id_campo],
            'Cod': [f"{new_code:02}"],
            'Label': [clean_label],
            'Agrupación': [None], 
            '# Pregunta del formulario': [form_question], 
            'Nombre de la Pregunta': [None]
        })
        # print(f"new_row: {new_row}")

        codes_df = pd.concat([codes_df, new_row], ignore_index=True)
        # print(f"Updated codes_df: {codes_df.tail()}")

    return codes_df


def update_used_columns(original_responses_df: pd.DataFrame, modified_responses_df: pd.DataFrame,
                       modified_columns: List[str], save_path: str) -> None:
    """Update only the used columns in the original dataframe"""
    for column in modified_columns:
        code_column = f'C{column}'
        if code_column in modified_responses_df.columns:
            if code_column not in original_responses_df.columns:
                original_responses_df[code_column] = ""
            
            original_responses_df[code_column] = modified_responses_df[code_column]
            
            # print(f"Verificando columna {code_column}...")
            # print(f"Registros vacíos encontrados: {original_responses_df[code_column].isna().sum()}")
            # print(f"Registros con string vacío: {(original_responses_df[code_column].astype(str) == '').sum()}")
    
    original_responses_df.to_excel(save_path, index=False)
    print(f"Updated file saved at {save_path}")


def stop_process() -> None:
    """Stop the processing"""
    global PROCESS_STOPPED
    PROCESS_STOPPED = True
    print("Proceso detenido por el usuario")


def reset_process_flag() -> None:
    """Reset the process stopped flag"""
    global PROCESS_STOPPED
    PROCESS_STOPPED = False


def get_frequent_responses(responses_df: pd.DataFrame, columns: List[str], top_n: int = 20, similarity_threshold: float = 80.0) -> Dict[str, List[Dict[str, Any]]]:
    """
    Analyze frequent responses for selected columns.
    Groups similar responses (fuzzy match >= 80%).
    
    Returns:
        Dict where keys are column names and values are lists of dicts:
        {'text': str, 'count': int, 'variations': List[str]}
    """
    from rapidfuzz import process, fuzz
    
    result = {}
    
    for col in columns:
        if col not in responses_df.columns:
            continue
            
        # 1. Get value counts of normalized text
        # We assume normalize_text is available in logic.py
        raw_values = responses_df[col].dropna().astype(str).tolist()
        normalized_counts = {}
        original_map = {} # norm -> list of originals
        
        for val in raw_values:
            norm = normalize_text(val)
            if not norm: continue
            
            normalized_counts[norm] = normalized_counts.get(norm, 0) + 1
            if norm not in original_map:
                original_map[norm] = set()
            original_map[norm].add(val)
            
        # Convert to list of dicts for sorting
        candidates = [{"text": norm, "count": count} for norm, count in normalized_counts.items()]
        candidates.sort(key=lambda x: x['count'], reverse=True)
        
        # 2. Group by similarity
        grouped_results = []
        processed_texts = set()
        
        for item in candidates:
            text = item['text']
            if text in processed_texts:
                continue
                
            processed_texts.add(text)
            
            group = {
                "text": text, # The representative text (most frequent)
                "count": item['count'],
                "variations": list(original_map[text])
            }
            
            # Look for similar items in the remaining candidates
            # We iterate through the rest to find matches
            # Ideally we only check against "unprocessed" items, but for simplicity/speed with rapidfuzz:
            
            # Let's extract remaining texts to compare against
            remaining_candidates = [c for c in candidates if c['text'] not in processed_texts]
            if not remaining_candidates:
                grouped_results.append(group)
                break
                
            remaining_texts = [c['text'] for c in remaining_candidates]
            
            # Find matches > threshold
            matches = process.extract(text, remaining_texts, scorer=fuzz.ratio, limit=None, score_cutoff=similarity_threshold)
            
            for match_text, score, index in matches:
                # rapidfuzz returns (match, score, index)
                processed_texts.add(match_text)
                
                # Add count to the main group
                match_candidate = next(c for c in remaining_candidates if c['text'] == match_text)
                group['count'] += match_candidate['count']
                group['variations'].extend(list(original_map[match_text]))
            
            # Pick the most frequent original variation as the display text (optional, but nicer)
            # For now, we keep the normalized representative or pick the first variation
            if group['variations']:
                 # Find most frequent original string? Too expensive maybe. Just pick shortest/first.
                 group['display_text'] = sorted(list(group['variations']), key=len)[0]
            else:
                 group['display_text'] = text

            grouped_results.append(group)
            
            if len(grouped_results) >= top_n:
                break
        
        # Sort grouped results by total count descending
        grouped_results.sort(key=lambda x: x['count'], reverse=True)
        
        # Filter groups with less than 10 mentions (User requirement)
        grouped_results = [g for g in grouped_results if g['count'] >= 10]
        
        result[col] = grouped_results
        
    return result


def apply_manual_coding(responses_df: pd.DataFrame, manual_mappings: Dict[str, Dict[str, str]], 
                       similarity_threshold: float = 80.0) -> Tuple[pd.DataFrame, Set[Tuple[int, str]]]:
    """
    Apply manual codes to the dataframe before AI processing.
    
    Args:
        responses_df: DataFrame to process
        manual_mappings: Dict {column_name: {text_to_match: code_to_assign}}
        similarity_threshold: Fuzzy match threshold (0-100)
        
    Returns:
        Tuple(processed_df, set_of_modified_cells)
    """
    from rapidfuzz import process, fuzz
    
    modified_cells = set()
    
    print("EJECUTANDO CODIFICACIÓN MANUAL")
    
    for col, mappings in manual_mappings.items():
        if col not in responses_df.columns:
            continue
            
        code_column = f'C{col}'
        if code_column not in responses_df.columns:
            responses_df[code_column] = ""
            
        # Normalize keys in mapping for consistent comparison
        normalized_map = {normalize_text(k): v for k, v in mappings.items()}
        map_keys = list(normalized_map.keys())
        
        # Iterate rows
        for idx in responses_df.index:
            # Skip if already coded (though usually this runs first)
            current_code = str(responses_df.at[idx, code_column]).strip()
            if current_code and current_code != "nan":
                continue
                
            val = responses_df.at[idx, col]
            if pd.isna(val) or str(val).strip() == "":
                continue
                
            norm_val = normalize_text(str(val))
            if not norm_val:
                continue
                
            assigned_code = None
            
            # 1. Exact Match (Normalized)
            if norm_val in normalized_map:
                assigned_code = normalized_map[norm_val]
            # else:
            #     # 2. Fuzzy Match (Disabled to respect manual discard/selection)
            #     # Since the frontend sends ALL validated variations as keys, exact match is sufficient.
            #     # This prevents "discarded" variations from being accidentally matched via fuzzy logic.
            #     if map_keys:
            #         match = process.extractOne(norm_val, map_keys, scorer=fuzz.ratio, score_cutoff=similarity_threshold)
            #         if match:
            #             match_text, score, index = match
            #             assigned_code = normalized_map[match_text]
            
            if assigned_code:
                # Assign code
                # Format to 2 digits just in case
                try:
                    formatted_code = f"{int(assigned_code):02d}"
                except:
                    formatted_code = str(assigned_code)
                    
                responses_df.at[idx, code_column] = formatted_code
                modified_cells.add((idx, code_column))
                
    return responses_df, modified_cells
