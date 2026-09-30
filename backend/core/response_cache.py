"""
Response Cache & Semantic Deduplication Engine
Provides zero-latency, zero-cost resolution for identical and rule-matched survey responses.
"""

import os
import re
import sqlite3
import hashlib
import unicodedata
from typing import Optional, Dict, Tuple, Set, Any
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "response_cache.sqlite3")

def normalize_response(text: str) -> str:
    """Normaliza el texto para comparación determinista insensible a mayúsculas, tildes y signos."""
    if not text:
        return ""
    s = str(text).strip().lower()
    # Remover tildes y diacríticos
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    # Normalizar puntuación y espacios
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def compute_question_hash(question_text: str, catalog_codes: Optional[Set[str]] = None) -> str:
    """Genera un hash determinista para el contexto de la pregunta y su catálogo."""
    norm_q = normalize_response(question_text)
    codes_str = ";".join(sorted(catalog_codes)) if catalog_codes else ""
    raw = f"{norm_q}::{codes_str}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

# Patrones deterministas para códigos especiales comunes
NONE_PATTERNS = {
    "nada", "ninguna", "ninguno", "ningun", "ningun aspecto", "ninguna razon",
    "todo bien", "todo perfecto", "todo esta bien", "todo esta perfecto",
    "nada en especial", "nada por ahora", "ninguno por ahora", "ninguna por ahora",
    "nada que mejorar", "nada por mejorar", "no hay nada", "no tengo quejas",
    "nada me disgusta", "todo excelente", "todo ok", "ninguna queja", "nada que decir"
}

UNKNOWN_PATTERNS = {
    "no se", "nose", "no responde", "no aplica", "no opina", "ns nr", "ns", "nr",
    "no tengo idea", "no sabria decir", "no sabria decirte", "no recuerdo", "no se acuerda",
    "no conozco", "sin comentarios", "no contesta", "na", "n a", "no aplica no responde",
    "no se no responde", "desconozco", "no sabe", "no sabe no responde"
}

def match_deterministic_rule(response_text: str, valid_codes_set: Set[str]) -> Optional[Tuple[str, str, float]]:
    """
    Verifica si una respuesta coincide con un patrón determinista universal de alta frecuencia.
    Retorna (codigo_asignado, routing_rule, confidence) si hay match, o None.
    """
    raw_str = str(response_text).strip()
    norm = normalize_response(raw_str)

    # 1. Respuestas de caracteres no alfanuméricos puros (signos, puntos, espacios)
    if not norm or re.match(r'^[\.\-_,\?\*!/\s]+$', raw_str):
        if "99" in valid_codes_set or not valid_codes_set:
            return "99", "RULE_PUNCTUATION_OR_EMPTY", 1.0

    # 2. Respuestas exactas tipo "Ninguno / Nada"
    if norm in NONE_PATTERNS:
        if "88" in valid_codes_set:
            return "88", "RULE_EXACT_NONE", 1.0

    # 3. Respuestas exactas tipo "No sabe / No responde"
    if norm in UNKNOWN_PATTERNS:
        if "99" in valid_codes_set:
            return "99", "RULE_EXACT_UNKNOWN", 1.0

    return None

class ResponseCache:
    """Caché híbrido en memoria y persistente en SQLite para deduplicación de respuestas."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "cache_hits": 0,
            "rule_hits": 0,
            "llm_calls": 0,
            "jev_fastpath": 0,
            "saved_tokens_approx": 0
        }
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS response_cache (
                        q_hash TEXT,
                        norm_response TEXT,
                        assigned_codes TEXT,
                        confidence REAL,
                        routing TEXT,
                        hit_count INTEGER DEFAULT 1,
                        updated_at TIMESTAMP,
                        PRIMARY KEY (q_hash, norm_response)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_lookup ON response_cache (q_hash, norm_response)")
        except Exception as e:
            print(f"Warning: No se pudo inicializar SQLite cache: {e}")

    def get(self, q_hash: str, response_text: str, valid_codes_set: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
        """Busca en reglas deterministas, luego en memoria y finalmente en SQLite."""
        norm = normalize_response(response_text)
        if not norm:
            return {
                "codes": "99",
                "confidence": 1.0,
                "routing": "RULE_EMPTY",
                "source": "rule"
            }

        # 1. Reglas deterministas universales
        if valid_codes_set:
            rule_match = match_deterministic_rule(response_text, valid_codes_set)
            if rule_match:
                codes, routing, conf = rule_match
                self.stats["rule_hits"] += 1
                self.stats["saved_tokens_approx"] += 360
                return {
                    "codes": codes,
                    "confidence": conf,
                    "routing": routing,
                    "source": "rule"
                }

        mem_key = f"{q_hash}::{norm}"

        # 2. Caché en memoria
        if mem_key in self._memory_cache:
            self.stats["cache_hits"] += 1
            self.stats["saved_tokens_approx"] += 360
            entry = self._memory_cache[mem_key]
            return {
                "codes": entry["assigned_codes"],
                "confidence": entry.get("confidence", 0.95),
                "routing": entry.get("routing", "CACHE_MEMORY"),
                "source": "memory"
            }

        # 3. Caché en SQLite persistente
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT assigned_codes, confidence, routing, hit_count FROM response_cache WHERE q_hash = ? AND norm_response = ?",
                    (q_hash, norm)
                )
                row = cursor.fetchone()
                if row:
                    codes, conf, routing, hits = row
                    cursor.execute(
                        "UPDATE response_cache SET hit_count = hit_count + 1, updated_at = ? WHERE q_hash = ? AND norm_response = ?",
                        (datetime.utcnow().isoformat(), q_hash, norm)
                    )
                    conn.commit()

                    # Guardar en memoria para futuras consultas inmediatas
                    self._memory_cache[mem_key] = {
                        "assigned_codes": codes,
                        "confidence": conf,
                        "routing": f"CACHE_SQLITE ({routing})"
                    }
                    self.stats["cache_hits"] += 1
                    self.stats["saved_tokens_approx"] += 360
                    return {
                        "codes": codes,
                        "confidence": conf,
                        "routing": f"CACHE_SQLITE ({routing})",
                        "source": "sqlite"
                    }
        except Exception as e:
            # Fallback silencioso si SQLite falla temporalmente
            pass

        return None

    def put(self, q_hash: str, response_text: str, assigned_codes: str, confidence: float = 0.9, routing: str = "LLM"):
        """Guarda un resultado en memoria y en SQLite."""
        norm = normalize_response(response_text)
        if not norm or not assigned_codes:
            return

        mem_key = f"{q_hash}::{norm}"
        self._memory_cache[mem_key] = {
            "assigned_codes": assigned_codes,
            "confidence": confidence,
            "routing": routing
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO response_cache (q_hash, norm_response, assigned_codes, confidence, routing, hit_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(q_hash, norm_response) DO UPDATE SET
                        assigned_codes = excluded.assigned_codes,
                        confidence = excluded.confidence,
                        routing = excluded.routing,
                        hit_count = hit_count + 1,
                        updated_at = excluded.updated_at
                """, (q_hash, norm, assigned_codes, confidence, routing, datetime.utcnow().isoformat()))
        except Exception as e:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return dict(self.stats)

# Singleton global para la aplicación
global_cache = ResponseCache()
