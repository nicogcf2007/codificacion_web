import importlib.util
from types import SimpleNamespace
import pytest


def test_engine_locked_contract_and_strict_parser():
    assert importlib.util.find_spec('modern.engine'), 'Immutable engine wrapper missing'
    from modern.engine import OpenAIProvider, parse_codes, build_messages
    calls=[]
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='01;02'))], usage=SimpleNamespace(prompt_tokens=20,completion_tokens=3))
    def create(**kwargs):
        calls.append(kwargs)
        return completion
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider=OpenAIProvider(client=client)
    categories=[{'code':'01','label':'Créditos'},{'code':'02','label':'Atención'}]
    result=provider.code('¿Por qué?', 'rápido y amable', categories, 2)
    assert result.raw == '01;02'
    assert calls[0]['model'] == 'gpt-6-luna'
    assert calls[0]['reasoning_effort'] == 'none'
    assert calls[0]['temperature'] == 0.0
    assert calls[0]['messages'] == build_messages('¿Por qué?', 'rápido y amable', categories,2)
    assert calls[0]['messages'][0]['content'].startswith('You are a Principal Survey Coding Methodologist')
    assert 'CRITICAL DISTINCTION 88 vs 99' in calls[0]['messages'][1]['content']
    assert parse_codes('01;02', categories,2) == (['01','02'],False)
    for text in ['1','01;99','01 extra','11','01;01','01;02;77','']:
        assert parse_codes(text,categories,2) == (['99'],True)
    assert parse_codes('88',categories,1) == (['88'],False)
    assert result.input_tokens == 20
