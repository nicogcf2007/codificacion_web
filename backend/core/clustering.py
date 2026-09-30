"""
Pre-agrupamiento Difuso y Deduplicación Semántica (Fuzzy Prototype Clustering)
Permite pre-limpiar respuestas vacías/símbolos y agrupar respuestas semánticamente similares (>=80%)
para codificar únicamente un prototipo representativo y propagar el código a todo el clúster.
"""

import re
import unicodedata
from typing import List, Dict, Set, Tuple, Any, Optional
from dataclasses import dataclass, field

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False


def normalize_text_clustering(text: Any) -> str:
    """Normaliza texto para comparación difusa: minúsculas, sin tildes, espacios colapsados."""
    if text is None:
        return ""
    s = str(text).strip().lower()
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def is_empty_or_symbol(text: Any) -> bool:
    """
    Detecta si una respuesta es nula, vacía, espacios en blanco o compuesta únicamente
    de signos de puntuación / símbolos (ej. '.', '-', '???', '///', '*', '_').
    """
    if text is None:
        return True
    s = str(text).strip()
    if not s or s.lower() in {"nan", "none", "null", "undefined"}:
        return True
    # Solo caracteres no alfanuméricos
    norm = normalize_text_clustering(s)
    if not norm or re.match(r'^[\.\-_,\?\*!/\\#\$%\^&\(\)\+=\{\}\[\]\|;:<>\s"\']+$', s):
        return True
    return False


def calculate_similarity(s1: str, s2: str) -> float:
    """Calcula similitud difusa (0 a 100) entre dos textos normalizados."""
    if s1 == s2:
        return 100.0
    if not s1 or not s2:
        return 0.0
    
    if HAS_RAPIDFUZZ:
        # token_set_ratio maneja permutaciones, palabras adicionales e inclusiones ("coca" en "me gusta la coca")
        return float(fuzz.token_set_ratio(s1, s2))
    else:
        # Fallback a difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio() * 100.0


@dataclass
class ClusterSummary:
    """Resumen de resultados del agrupamiento."""
    total_records: int
    unique_responses: int
    empty_count: int
    prototypes_count: int
    saved_ai_calls: int
    compression_pct: float
    prototype_map: Dict[str, str] = field(default_factory=dict) # response -> prototype
    cluster_members: Dict[str, List[str]] = field(default_factory=dict) # prototype -> [responses]
    empty_responses: Set[str] = field(default_factory=set)


def cluster_survey_responses(
    responses: List[Any],
    similarity_threshold: float = 80.0,
    min_length_for_clustering: int = 4
) -> ClusterSummary:
    """
    Agrupa una lista de respuestas abiertas:
    1. Pre-limpia vacíos y símbolos.
    2. Respuestas ultra-cortas (1-3 caracteres) solo se agrupan si son idénticas normalizadas.
    3. Agrupa por similitud difusa (>= similarity_threshold, por defecto 80.0%).
    4. Elige como prototipo la respuesta más concisa y limpia del grupo.
    
    Retorna ClusterSummary con el mapeo y estadísticas.
    """
    total_records = len(responses)
    empty_set: Set[str] = set()
    valid_responses_with_counts: Dict[str, int] = {}

    for raw in responses:
        if is_empty_or_symbol(raw):
            empty_set.add(str(raw) if raw is not None else "")
        else:
            raw_str = str(raw).strip()
            valid_responses_with_counts[raw_str] = valid_responses_with_counts.get(raw_str, 0) + 1

    unique_valid = list(valid_responses_with_counts.keys())
    # Ordenar por frecuencia descendente para que la más común tenga preferencia como prototipo
    unique_valid.sort(key=lambda x: (-valid_responses_with_counts[x], len(x)))

    clusters: Dict[str, List[str]] = {} # norm_proto -> list of raw strings
    proto_raw_map: Dict[str, str] = {} # norm_proto -> best raw representation
    resp_to_proto: Dict[str, str] = {} # raw -> proto_raw

    for raw in unique_valid:
        norm = normalize_text_clustering(raw)
        
        # Respuestas cortas o códigos numéricos no se agrupan difusamente para evitar falsos positivos
        if len(norm) < min_length_for_clustering:
            clusters[norm] = [raw]
            proto_raw_map[norm] = raw
            resp_to_proto[raw] = raw
            continue

        assigned_cluster = None
        best_score = 0.0

        for proto_norm in clusters.keys():
            score = calculate_similarity(norm, proto_norm)
            if score >= similarity_threshold and score > best_score:
                best_score = score
                assigned_cluster = proto_norm

        if assigned_cluster is not None:
            clusters[assigned_cluster].append(raw)
            resp_to_proto[raw] = proto_raw_map[assigned_cluster]
        else:
            # Nuevo clúster donde 'raw' es el prototipo inicial
            clusters[norm] = [raw]
            proto_raw_map[norm] = raw
            resp_to_proto[raw] = raw

    # Reestructurar diccionario de miembros con la versión cruda del prototipo
    final_cluster_members: Dict[str, List[str]] = {}
    for norm_key, members in clusters.items():
        proto_raw = proto_raw_map[norm_key]
        final_cluster_members[proto_raw] = members

    prototypes_count = len(clusters)
    unique_responses = len(unique_valid) + len(empty_set)
    saved_calls = max(0, len(unique_valid) - prototypes_count)
    compression = (saved_calls / len(unique_valid) * 100.0) if len(unique_valid) > 0 else 0.0

    return ClusterSummary(
        total_records=total_records,
        unique_responses=unique_responses,
        empty_count=len(empty_set),
        prototypes_count=prototypes_count,
        saved_ai_calls=saved_calls,
        compression_pct=round(compression, 1),
        prototype_map=resp_to_proto,
        cluster_members=final_cluster_members,
        empty_responses=empty_set
    )
