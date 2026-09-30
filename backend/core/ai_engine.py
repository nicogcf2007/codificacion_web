"""
AI Coding Engine - Multi-Model Hybrid & Resilient Architecture
Supports:
- hybrid_luna (Jev Fast-Path + GPT-6-Luna Escalation - Default / Masivo)
- hybrid_sol (Jev Fast-Path + GPT-6.1-SOL Escalation - Máxima Calidad C-Level)
- jev_express (Jev TypeSafe System One Puro - Ultra Rápido)
- luna_direct (GPT-6-Luna Directo)
- sol_direct (GPT-6.1-SOL Directo)
- luna56_direct (GPT-5.6-Luna Directo)
"""

import os
import re
import sys
import time
import asyncio
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Asegurar importación de core
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.response_cache import global_cache, compute_question_hash, normalize_response
from core.universal_coding import build_jev_plan, compose_jev_result

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY")

try:
    from typesafe_sdk import TypeSafeClient
    typesafe_client = TypeSafeClient(api_key=TYPESAFE_API_KEY) if TYPESAFE_API_KEY else None
except Exception as e:
    typesafe_client = None
    print(f"Warning: TypeSafe client could not be initialized: {e}")

openai_sync_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
openai_async_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

@dataclass
class CodingResult:
    codes: str
    codes_list: List[str]
    confidence: float
    routing: str
    status: str  # "AUTO_CODED" o "REVIEW_REQUIRED"
    is_cached: bool = False
    latency: float = 0.0
    new_label_needed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

def parse_llm_numbers(raw_text: str, valid_codes_set: Set[str], max_labels: int = 3) -> List[str]:
    """Extrae códigos válidos del texto de salida del LLM."""
    if not raw_text:
        return ["99"] if "99" in valid_codes_set else []
    
    # Buscar patrones de números
    numbers = re.findall(r'\b\d+\b', str(raw_text))
    assigned = []
    for n in numbers:
        code_str = str(int(n))
        code_fmt = f"{int(n):02d}"
        target = None
        if code_str in valid_codes_set:
            target = code_fmt
        elif code_fmt in valid_codes_set:
            target = code_fmt
        elif str(n) in valid_codes_set:
            target = str(n)
            
        if target and target not in assigned:
            assigned.append(target)
            if len(assigned) >= max_labels:
                break
                
    if not assigned:
        if "NEW_LABEL_NEEDED" in raw_text.upper():
            return ["77"] if "77" in valid_codes_set else ["99"]
        return ["99"] if "99" in valid_codes_set else ["77"]
        
    return assigned

class AICodingEngine:
    """Motor central de codificación con soporte para múltiples modos y caché inteligente."""

    def __init__(self, default_mode: str = "hybrid_luna"):
        self.default_mode = default_mode
        self.cache = global_cache

    def build_openai_messages(self, question: str, response: str, catalog: List[Dict[str, str]], context: str = "", max_labels: int = 3) -> List[Dict[str, str]]:
        labels_str = "\n".join([f"[{e['code']}] {e['label']}" for e in catalog])
        ctx_prompt = f"\nStudy context / Question: {context}" if context else ""
        return [
            {
                "role": "system",
                "content": (
                    "You are a Principal Survey Coding Methodologist at the National Consulting Center (CNC).\n"
                    "Your task is to accurately map open-ended survey responses into the official numeric codebook provided below.\n"
                    "The respondents speak in Colombian Spanish; evaluate semantic intent, idioms, and colloquialisms with precision."
                )
            },
            {
                "role": "user",
                "content": f"""Survey Question: {question}{ctx_prompt}

Official Codebook:
{labels_str}

Respondent Response: "{response}"

STRICT METHODOLOGICAL CODING GUIDELINES (PARSIMONY & DISAMBIGUATION):
1. PRINCIPLE OF PARSIMONY: Assign the single most specific, direct code that captures the user's primary statement. Never extrapolate unwritten motives.
2. CRITICAL DISTINCTION 88 vs 99 (AVOID FALSE UNKNOWNS):
   - Assign CODE 88 if the respondent expresses loyalty, satisfaction, states they would NOT switch entities, has no complaints, or indicates 'nothing to improve' (e.g., 'no la cambio', 'estoy bien con ellos', 'nada por ahora', 'ninguna sugerencia').
   - Assign CODE 99 ONLY if the response is purely 'no sé' (don't know), 'no responde', gibberish, punctuation signs, or completely empty.
3. TIE-BREAKER FOR OVERLAPPING CATEGORIES:
   - If speed/turnaround is mentioned specifically with loans or disbursement ('rápido para los préstamos'), prioritize the loan speed code over general operational speed.
   - If paperwork or lack of guarantors is mentioned, prioritize documentation/requirements over general speed.
4. MULTI-CODE CRITERIA:
   - Only assign multiple codes (up to {max_labels}) if the user explicitly articulates distinct, independent ideas connected by conjunctions ('y', 'además', 'pero').
5. NO MATCHING CATEGORY: If it is a valid distinct idea not covered in the codebook, assign CODE 77 (Other).
6. OUTPUT FORMAT: Respond ONLY with the assigned numeric codes separated by semicolons (e.g., 01 or 01;05). No explanations, no extra text."""
            }
        ]

    def _call_jev_single(self, question: str, response: str, catalog: List[Dict[str, str]], max_labels: int = 3) -> Tuple[List[str], float, str]:
        """Ejecuta clasificación ultra-rápida con Jev System One."""
        if not typesafe_client:
            return [], 0.0, "JEV_CLIENT_UNAVAILABLE"

        cat_codes = {e["code"] for e in catalog}
        jev_entries = [dict(e) for e in catalog]
        if "77" not in cat_codes:
            jev_entries.append({"code": "77", "label": "Otro", "description": "Otro"})
        if "88" not in cat_codes:
            jev_entries.append({"code": "88", "label": "Ninguno", "description": "Ninguno / Nada"})
        if "99" not in cat_codes:
            jev_entries.append({"code": "99", "label": "No sabe / No responde", "description": "No sabe o no responde"})

        for e in jev_entries:
            if "description" not in e:
                e["description"] = e["label"]

        req = {
            "question": {"text": question},
            "response": {"text": response},
            "taxonomy": {
                "mode": "multi_label" if max_labels > 1 else "single_label",
                "max_labels": max_labels,
                "entries": jev_entries
            },
            "policy": {
                "special_codes": {"other": "77", "none": "88", "unknown": "99"},
                "auto_code_confidence": 0.60,
                "auto_code_margin": 0.15
            }
        }

        try:
            plan = build_jev_plan(req)
            resp = typesafe_client.system_one(state=plan["state"], questions=plan["questions"])
            outputs = {}
            for k, ans in resp.answers.items():
                outputs[k] = {
                    "choice": getattr(ans, "choice", None),
                    "confidence": getattr(ans, "confidence", None),
                    "probabilities": getattr(ans, "probabilities", None),
                    "noul": getattr(ans, "noul", None)
                }
            comp = compose_jev_result(plan, outputs)
            raw_codes = comp.get("codes", [])
            # Formatear códigos con 2 dígitos
            formatted = []
            for c in raw_codes:
                if str(c).isdigit():
                    formatted.append(f"{int(c):02d}")
                else:
                    formatted.append(str(c))
            conf = float(comp.get("signals", {}).get("primary_confidence", comp.get("signals", {}).get("kind_confidence", 0.85)))
            status = comp.get("status", "REVIEW_REQUIRED")
            return formatted, conf, status
        except Exception as err:
            return [], 0.0, f"ERR_{err}"

    def code_single(
        self,
        question: str,
        response: str,
        catalog: List[Dict[str, str]],
        mode: Optional[str] = None,
        max_labels: int = 3,
        context: str = "",
        use_cache: bool = True
    ) -> CodingResult:
        """Codifica una respuesta única aplicando Caché -> Fast-Path -> Escalado según el modo seleccionado."""
        t0 = time.time()
        active_mode = mode or self.default_mode
        valid_codes_set = {str(e["code"]) for e in catalog} | {f"{int(e['code']):02d}" for e in catalog if str(e["code"]).isdigit()}
        valid_codes_set.update({"77", "88", "99"})
        q_hash = compute_question_hash(question, {e["code"] for e in catalog})

        # 1. Capa de Caché Semántico y Deduplicación
        if use_cache:
            cached = self.cache.get(q_hash, response, valid_codes_set)
            if cached:
                c_str = cached["codes"]
                c_list = [c.strip() for c in c_str.split(";") if c.strip()]
                return CodingResult(
                    codes=c_str,
                    codes_list=c_list,
                    confidence=float(cached.get("confidence", 1.0)),
                    routing=cached.get("routing", "CACHE_HIT"),
                    status="AUTO_CODED",
                    is_cached=True,
                    latency=time.time() - t0
                )

        # 2. Modo: Jev Express
        if active_mode == "jev_express":
            j_codes, j_conf, j_status = self._call_jev_single(question, response, catalog, max_labels)
            if not j_codes:
                j_codes = ["99"]
            codes_str = ";".join(j_codes)
            res = CodingResult(
                codes=codes_str,
                codes_list=j_codes,
                confidence=j_conf,
                routing="JEV_EXPRESS",
                status=j_status,
                latency=time.time() - t0
            )
            if use_cache and j_status == "AUTO_CODED":
                self.cache.put(q_hash, response, codes_str, j_conf, "JEV_EXPRESS")
            return res

        # 3. Modo: Híbrido (Fast-Path Jev -> Escalado)
        if active_mode in ["hybrid_luna", "hybrid_sol"]:
            # Paso A: Jev Fast-Path
            j_codes, j_conf, j_status = self._call_jev_single(question, response, catalog, max_labels)
            # Si Jev resolvió con alta confianza y no es ambiguo (no es 77 ni 99 incierto)
            if j_status == "AUTO_CODED" and j_codes and j_codes != ["99"] and j_codes != ["77"]:
                codes_str = ";".join(j_codes)
                if use_cache:
                    self.cache.put(q_hash, response, codes_str, j_conf, "JEV_FASTPATH")
                return CodingResult(
                    codes=codes_str,
                    codes_list=j_codes,
                    confidence=j_conf,
                    routing="JEV_FASTPATH",
                    status="AUTO_CODED",
                    latency=time.time() - t0
                )

            # Paso B: Escalado a LLM Arbitro
            escalated_model = "gpt-6.1-sol" if active_mode == "hybrid_sol" else "gpt-6-luna"
            routing_tag = "ESCALATED_SOL" if active_mode == "hybrid_sol" else "ESCALATED_LUNA"
            
            try:
                msgs = self.build_openai_messages(question, response, catalog, context, max_labels)
                call_args = {
                    "model": escalated_model,
                    "messages": msgs,
                    "reasoning_effort": "low",
                    "max_completion_tokens": 200
                }
                resp = openai_sync_client.chat.completions.create(**call_args)
                raw_out = (resp.choices[0].message.content or "").strip()
                parsed_codes = parse_llm_numbers(raw_out, valid_codes_set, max_labels)
                codes_str = ";".join(parsed_codes)
                
                # Definir estado de revisión
                status = "AUTO_CODED" if parsed_codes != ["77"] and len(parsed_codes) > 0 else "REVIEW_REQUIRED"
                conf = 0.90 if status == "AUTO_CODED" else 0.50

                if use_cache and status == "AUTO_CODED":
                    self.cache.put(q_hash, response, codes_str, conf, routing_tag)

                return CodingResult(
                    codes=codes_str,
                    codes_list=parsed_codes,
                    confidence=conf,
                    routing=routing_tag,
                    status=status,
                    latency=time.time() - t0,
                    details={"raw_llm": raw_out}
                )
            except Exception as err:
                print(f"Error en escalado a {escalated_model}: {err}")
                # Fallback a códigos de Jev si existían, o 99
                fallback = j_codes if j_codes else ["99"]
                return CodingResult(
                    codes=";".join(fallback),
                    codes_list=fallback,
                    confidence=0.30,
                    routing=f"FALLBACK_{routing_tag}",
                    status="REVIEW_REQUIRED",
                    latency=time.time() - t0
                )

        # 4. Modos Directos (Luna 6, SOL 6.1, Luna 5.6)
        direct_models = {
            "luna_direct": "gpt-6-luna",
            "sol_direct": "gpt-6.1-sol",
            "luna56_direct": "gpt-5.6-luna"
        }
        model_name = direct_models.get(active_mode, "gpt-6-luna")
        try:
            msgs = self.build_openai_messages(question, response, catalog, context, max_labels)
            resp = openai_sync_client.chat.completions.create(
                model=model_name,
                messages=msgs,
                reasoning_effort="low",
                max_completion_tokens=200
            )
            raw_out = (resp.choices[0].message.content or "").strip()
            parsed_codes = parse_llm_numbers(raw_out, valid_codes_set, max_labels)
            codes_str = ";".join(parsed_codes)
            status = "AUTO_CODED" if parsed_codes != ["77"] else "REVIEW_REQUIRED"
            conf = 0.92 if status == "AUTO_CODED" else 0.50

            if use_cache and status == "AUTO_CODED":
                self.cache.put(q_hash, response, codes_str, conf, f"DIRECT_{model_name}")

            return CodingResult(
                codes=codes_str,
                codes_list=parsed_codes,
                confidence=conf,
                routing=f"DIRECT_{model_name}",
                status=status,
                latency=time.time() - t0
            )
        except Exception as err:
            return CodingResult(
                codes="99",
                codes_list=["99"],
                confidence=0.1,
                routing=f"ERROR_{model_name}",
                status="REVIEW_REQUIRED",
                latency=time.time() - t0
            )

# Instancia global del motor
global_ai_engine = AICodingEngine()
