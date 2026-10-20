"""Immutable methodological wrapper. Provider failures are never coded as 99."""
from __future__ import annotations
from dataclasses import dataclass
import os
import re

MODEL = 'gpt-6-luna'
REASONING_EFFORT = 'none'
TEMPERATURE = 0.0
CLUSTER_THRESHOLD = 85.0


def build_messages(question, response, categories, max_labels):
    labels_str = '\n'.join(f"[{entry['code']}] {entry['label']}" for entry in categories)
    return [
        {'role': 'system', 'content':
            'You are a Principal Survey Coding Methodologist at the National Consulting Center (CNC).\n'
            'Your task is to accurately map open-ended survey responses into the official numeric codebook provided below.\n'
            'The respondents speak in Colombian Spanish; evaluate semantic intent, idioms, and colloquialisms with precision.'},
        {'role':'user', 'content':f'''Survey Question: {question}

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
6. OUTPUT FORMAT: Respond ONLY with the assigned numeric codes separated by semicolons (e.g., 01 or 01;05). No explanations, no extra text.'''}]


def parse_codes(raw, categories, max_labels):
    text = (raw or '').strip()
    codes = text.split(';')
    allowed = {entry['code'] for entry in categories} | {'77','88','99'}
    valid = (re.fullmatch(r'[0-9]{2}(;[0-9]{2})*', text) is not None
             and len(codes) <= max_labels and len(set(codes)) == len(codes)
             and set(codes) <= allowed and not (set(codes) & {'88','99'} and len(codes)>1))
    return (codes, False) if valid else (['99'], True)


@dataclass(frozen=True)
class Inference:
    raw: str
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderPaused(Exception):
    def __init__(self, reason, uncertain=False):
        super().__init__(reason)
        self.reason = reason
        self.uncertain = uncertain


class BlockedProvider:
    mode = 'blocked'

    def code(self, *args):
        raise ProviderPaused('Proveedor bloqueado. Configure un proveedor antes de iniciar.')


class DemoProvider:
    """Explicit simulation only: not a semantic benchmark or a replacement engine."""
    mode = 'demo'

    def code(self, question, text, categories, max_labels):
        import time
        time.sleep(0.15)
        norm = text.casefold()
        if any(fragment in norm for fragment in ('nada', 'no la cambio', 'ninguna')):
            return Inference('88')
        if any(fragment in norm for fragment in ('no sé', 'no se', 'no responde')):
            return Inference('99')
        for category in categories:
            words = re.findall(r'\w+', category['label'].casefold())
            if any(len(word) > 3 and word[:5] in norm for word in words):
                return Inference(category['code'])
        return Inference('77')


class OpenAIProvider:
    mode = 'openai'

    def __init__(self, client=None, api_key=None):
        self.client = client
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')

    def set_key(self, key):
        self.api_key = key
        self.client = None

    def code(self, question, text, categories, max_labels):
        if self.client is None:
            if not self.api_key:
                raise ProviderPaused('Credencial de OpenAI ausente. Actualice la API Key.')
            from openai import OpenAI
            # No SDK auto-retries: an ambiguous network outcome must not double-bill.
            self.client = OpenAI(api_key=self.api_key, max_retries=0, timeout=60)
        try:
            result = self.client.chat.completions.create(
                model=MODEL, reasoning_effort=REASONING_EFFORT, temperature=TEMPERATURE,
                messages=build_messages(question, text, categories, max_labels),
                max_completion_tokens=200)
        except Exception as exc:
            status = getattr(exc, 'status_code', None)
            if status == 401:
                raise ProviderPaused('Credencial de OpenAI inválida. Actualice la API Key y reanude.') from None
            if status == 429:
                raise ProviderPaused('Saldo insuficiente o cuota excedida en OpenAI. Recargue créditos y reanude.') from None
            if status and status < 500:
                raise ProviderPaused(f'OpenAI rechazó la solicitud (HTTP {status}). Verifique modelo y parámetros; no se cambia el motor.') from None
            raise ProviderPaused('Resultado incierto: fallo de red o del proveedor. Reintentar podría generar otro cargo.', uncertain=True) from None
        usage = result.usage
        return Inference(result.choices[0].message.content or '',
                         getattr(usage, 'prompt_tokens', 0) or 0,
                         getattr(usage, 'completion_tokens', 0) or 0)


def provider_for(mode):
    return {'blocked': BlockedProvider, 'demo': DemoProvider, 'openai': OpenAIProvider}[mode]()
