import pytest


@pytest.mark.parametrize('name,value',[
    ('INPUT_USD_PER_MILLION','bad-rate'),
    ('OUTPUT_USD_PER_MILLION','-0.5'),
    ('BASELINE_RECORD_USD','nan'),
    ('BASELINE_RECORD_USD','inf'),
])
def test_invalid_financial_configuration_fails_before_any_coding(factory,monkeypatch,name,value):
    monkeypatch.setenv(name,value)
    with pytest.raises(ValueError,match=name):
        factory()
