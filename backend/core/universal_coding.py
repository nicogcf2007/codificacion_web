"""Núcleo universal para codificación zero-shot de encuestas.

No contiene preguntas ni umbrales aprendidos de una encuesta concreta.
La política reserva únicamente 77/88/99 para other/none/unknown.
Los modelos ven semántica y claves neutrales; los códigos permanecen opacos en código.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from typesafe_sdk import Choice, Noul


class InvalidCodingRequest(ValueError):
    """La solicitud no permite una clasificación semántica segura."""


SPECIAL_NAMES = ("other", "none", "unknown")


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(request)
    try:
        question_text = normalized["question"]["text"]
        response_text = normalized["response"]["text"]
        taxonomy = normalized["taxonomy"]
        entries = taxonomy["entries"]
        mode = taxonomy["mode"]
        special_codes = normalized["policy"]["special_codes"]
    except (KeyError, TypeError) as exc:
        raise InvalidCodingRequest(f"Falta un campo obligatorio: {exc}") from exc

    if not isinstance(question_text, str) or not isinstance(response_text, str):
        raise InvalidCodingRequest("question.text y response.text deben ser strings.")
    question_text = question_text.strip()
    response_text = response_text.strip()
    if not question_text:
        raise InvalidCodingRequest("La pregunta no puede estar vacía.")
    if mode not in {"single_label", "multi_label"}:
        raise InvalidCodingRequest("taxonomy.mode debe ser single_label o multi_label.")
    if not isinstance(entries, list) or not entries:
        raise InvalidCodingRequest("El catálogo no puede estar vacío.")
    if special_codes != {"other": "77", "none": "88", "unknown": "99"}:
        raise InvalidCodingRequest("Los códigos especiales son exactamente other=77, none=88, unknown=99.")
    for field in ("auto_code_confidence", "auto_code_margin", "additional_confidence", "other_threshold"):
        if field in normalized["policy"] and not _unit_number(normalized["policy"][field]):
            raise InvalidCodingRequest(f"policy.{field} debe ser un número finito entre 0 y 1.")

    codes: list[str] = []
    semantic_entries = 0
    for entry in entries:
        if not isinstance(entry, dict) or "code" not in entry:
            raise InvalidCodingRequest("Cada entrada requiere code, label y/o description.")
        code = entry["code"]
        if not isinstance(code, str) or not code:
            raise InvalidCodingRequest("Los códigos deben ser strings no vacíos y se preservan literalmente.")
        codes.append(code)
        label = str(entry.get("label") or "").strip()
        description = str(entry.get("description") or "").strip()
        if label or description:
            semantic_entries += 1
    if len(codes) != len(set(codes)):
        raise InvalidCodingRequest("El catálogo contiene códigos duplicados.")
    if semantic_entries != len(entries):
        raise InvalidCodingRequest("Cada código requiere contenido semántico interpretable.")

    for name in SPECIAL_NAMES:
        code = special_codes[name]
        if not isinstance(code, str) or code not in codes:
            raise InvalidCodingRequest(f"El código especial {name} no existe en el catálogo.")
    if len(set(special_codes.values())) != 3:
        raise InvalidCodingRequest("77/88/99 o sus equivalentes deben ser distintos.")

    if mode == "single_label":
        taxonomy["max_labels"] = 1
    else:
        max_labels = taxonomy.get("max_labels")
        if type(max_labels) is not int or not 1 <= max_labels <= 3:
            raise InvalidCodingRequest("multi_label soporta max_labels entero entre 1 y 3.")
    normalized["response"]["text"] = response_text
    normalized["question"]["text"] = question_text
    return normalized


def _regular_entries(request: dict[str, Any]) -> list[dict[str, Any]]:
    special = set(request["policy"]["special_codes"].values())
    return [entry for entry in request["taxonomy"]["entries"] if entry["code"] not in special]


def select_strategy(request: dict[str, Any]) -> str:
    normalized = validate_request(request)
    regular_count = len(_regular_entries(normalized))
    mode = normalized["taxonomy"]["mode"]
    # Choice admite 255 opciones: reservar una para no_match/no_additional.
    if regular_count > 254:
        return "retrieval_multi" if mode == "multi_label" else "retrieval_single"
    if normalized["taxonomy"].get("hierarchical"):
        # Clasificación plana de hojas; no implica traversal ni validación de padres.
        return "flat_hierarchical_multi" if mode == "multi_label" else "flat_hierarchical_single"
    return "flat_multi" if mode == "multi_label" else "flat_single"


def _semantic_description(entry: dict[str, Any], structured: bool) -> Any:
    label = str(entry.get("label") or "").strip()
    description = str(entry.get("description") or "").strip()
    if not structured:
        return ": ".join(value for value in [label, description] if value)
    result: dict[str, Any] = {"meaning": description or label}
    if label and description and label.casefold() not in description.casefold():
        result["label"] = label
    if entry.get("inclusions"):
        result["includes"] = list(entry["inclusions"])
    if entry.get("exclusions"):
        result["excludes"] = list(entry["exclusions"])
    if entry.get("examples"):
        result["examples"] = list(entry["examples"])
    return result


def build_jev_plan(request: dict[str, Any], variant: str = "structured") -> dict[str, Any]:
    normalized = validate_request(request)
    strategy = select_strategy(normalized)
    if strategy.startswith("retrieval_"):
        raise InvalidCodingRequest("Más de 254 códigos regulares requieren recuperación (una opción se reserva).")

    regular = _regular_entries(normalized)
    option_to_code = {f"c{index:03d}": entry["code"] for index, entry in enumerate(regular)}
    criteria = {
        option: _semantic_description(entry, structured=variant == "structured")
        for option, entry in zip(option_to_code, regular)
    }
    catalog_state = [
        {
            "option": option,
            "meaning": _semantic_description(entry, structured=True),
        }
        for option, entry in zip(option_to_code, regular)
    ]
    state = {
        "survey_question": normalized["question"]["text"],
        "open_response": normalized["response"]["text"],
        "catalog": catalog_state,
        "mode": normalized["taxonomy"]["mode"],
    }
    kind_instructions: Any
    if variant == "concise":
        kind_instructions = "Clasifica el estado de la respuesta abierta frente al catálogo suministrado."
    else:
        kind_instructions = {
            "task": "Clasifica el estado de la respuesta frente a la pregunta y al catálogo.",
            "rules": [
                "Una incertidumbre parcial no es unknown si existe contenido sustantivo clasificable.",
                "Other exige contenido pertinente interpretable que no esté cubierto por el catálogo.",
                "None exige ausencia explícita de opciones aplicables.",
            ],
        }
    questions: dict[str, Any] = {
        "kind": Choice(
            instructions=kind_instructions,
            criteria={
                "substantive": "Existe contenido sustantivo cubierto por una o más categorías del catálogo.",
                "other": "Existe contenido pertinente e interpretable, pero no está cubierto por ninguna categoría.",
                "none": "La persona dice explícitamente que ninguna opción aplica, que nada ocurrió o que no hubo motivo.",
                "unknown": "No sabe, no responde, rechaza responder o el texto es ininterpretable.",
            },
        ),
        "primary": Choice(
            instructions="Selecciona la categoría regular que mejor representa la idea principal, o no_match si ninguna aplica.",
            criteria={**criteria, "no_match": "Ninguna categoría regular representa el contenido de la respuesta."},
        ),
    }
    if normalized["taxonomy"]["mode"] == "multi_label":
        additional_criteria = {
            **criteria,
            "no_additional": "No existe otra idea independiente cubierta por una categoría regular distinta.",
        }
        questions["secondary"] = Choice(
            instructions="Selecciona una segunda categoría regular solo para una idea independiente adicional.",
            criteria=additional_criteria,
        )
        questions["tertiary"] = Choice(
            instructions="Selecciona una tercera categoría regular solo para otra idea independiente adicional.",
            criteria=additional_criteria,
        )
        questions["uncovered"] = Noul(
            instructions="¿La respuesta contiene además una idea pertinente e interpretable no cubierta por ninguna categoría regular del catálogo?",
            criteria={
                "true": "Hay una idea sustantiva fuera del catálogo, aunque otras ideas sí estén cubiertas.",
                "false": "Todas las ideas pertinentes están cubiertas o no hay contenido sustantivo.",
            },
        )
    return {
        "request": normalized,
        "state": state,
        "questions": questions,
        "option_to_code": option_to_code,
        "strategy": strategy,
        "variant": variant,
    }


def _unit_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def _valid_choice(answer: Any, options: set[str]) -> bool:
    if not isinstance(answer, dict) or not _unit_number(answer.get("confidence")):
        return False
    choice = answer.get("choice")
    probabilities = answer.get("probabilities")
    if not isinstance(choice, str) or choice not in options:
        return False
    if not isinstance(probabilities, dict) or set(probabilities) != options:
        return False
    if not all(_unit_number(value) for value in probabilities.values()):
        return False
    return (
        math.isclose(sum(probabilities.values()), 1.0, rel_tol=0.0, abs_tol=1e-6)
        and probabilities[choice] == max(probabilities.values())
    )


def _choice_margin(answer: dict[str, Any]) -> float:
    values = sorted(
        [float(value) for value in answer.get("probabilities", {}).values() if math.isfinite(float(value))],
        reverse=True,
    )
    if not values:
        return 0.0
    return values[0] - (values[1] if len(values) > 1 else 0.0)


def compose_jev_result(plan: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
    # Raw concentration thresholds are heuristics, not calibrated correctness probabilities.
    request = plan["request"]
    policy = request["policy"]
    special = policy["special_codes"]
    kind = outputs.get("kind") if isinstance(outputs, dict) else None
    if not _valid_choice(kind, set(plan["questions"]["kind"].criteria)):
        return {"status": "ABSTAINED", "codes": [], "routing_reasons": ["invalid_or_missing_kind"], "signals": {}}
    kind_choice = kind.get("choice")
    kind_confidence = float(kind.get("confidence", 0.0) or 0.0)
    confidence_threshold = float(policy.get("auto_code_confidence", 0.6))
    margin_threshold = float(policy.get("auto_code_margin", 0.15))

    special_map = {"other": special["other"], "none": special["none"], "unknown": special["unknown"]}
    if kind_choice in special_map:
        status = "AUTO_CODED" if kind_confidence >= confidence_threshold else "REVIEW_REQUIRED"
        return {
            "status": status,
            "codes": [special_map[kind_choice]],
            "routing_reasons": [] if status == "AUTO_CODED" else ["low_kind_confidence"],
            "signals": {"kind_confidence": kind_confidence},
        }

    primary = outputs.get("primary", {})
    if not _valid_choice(primary, set(plan["questions"]["primary"].criteria)):
        return {"status": "ABSTAINED", "codes": [], "routing_reasons": ["invalid_or_missing_primary"], "signals": {"kind_confidence": kind_confidence}}
    primary_option = primary.get("choice")
    primary_code = plan["option_to_code"].get(primary_option)
    if primary_code is None:
        return {
            "status": "ABSTAINED",
            "codes": [],
            "routing_reasons": ["invalid_or_missing_primary"],
            "signals": {"kind_confidence": kind_confidence},
        }

    primary_confidence = float(primary.get("confidence", 0.0) or 0.0)
    primary_margin = _choice_margin(primary)
    codes = [primary_code]
    reasons: list[str] = []
    uncovered = None
    if request["taxonomy"]["mode"] == "multi_label":
        additional_threshold = float(policy.get("additional_confidence", confidence_threshold))
        for name in ("secondary", "tertiary"):
            if len(codes) >= request["taxonomy"]["max_labels"]:
                break
            answer = outputs.get(name, {})
            if not _valid_choice(answer, set(plan["questions"][name].criteria)):
                reasons.append(f"invalid_or_missing_{name}")
                continue
            option = answer.get("choice")
            code = plan["option_to_code"].get(option)
            confidence = float(answer.get("confidence", 0.0) or 0.0)
            if code and code not in codes and confidence >= additional_threshold:
                codes.append(code)
            if len(codes) >= request["taxonomy"]["max_labels"]:
                break
        if request["taxonomy"].get("exhaustiveness") == "open" and len(codes) < request["taxonomy"]["max_labels"]:
            answer = outputs.get("uncovered")
            if not isinstance(answer, dict) or not _unit_number(answer.get("noul")):
                reasons.append("invalid_or_missing_uncovered")
            else:
                uncovered = float(answer["noul"])
                if uncovered >= float(policy.get("other_threshold", 0.7)):
                    codes.append(special["other"])

    if kind_confidence < confidence_threshold:
        reasons.append("low_kind_confidence")
    if primary_confidence < confidence_threshold:
        reasons.append("low_primary_confidence")
    if primary_margin < margin_threshold:
        reasons.append("low_primary_margin")
    status = "REVIEW_REQUIRED" if reasons else "AUTO_CODED"
    return {
        "status": status,
        "codes": codes,
        "routing_reasons": reasons,
        "signals": {
            "kind_confidence": kind_confidence,
            "primary_confidence": primary_confidence,
            "primary_margin": primary_margin,
            "uncovered": uncovered,
        },
    }


def _valid_prediction(prediction: dict[str, Any], valid_codes: set[str]) -> bool:
    codes = prediction.get("codes")
    if not isinstance(codes, list) or not codes or any(code not in valid_codes for code in codes):
        return False
    specials = {"77", "88", "99"} & set(codes)
    if ("88" in specials or "99" in specials) and len(codes) > 1:
        return False
    return not ({"88", "99"} <= specials)


def reconcile_predictions(
    jev: dict[str, Any],
    luna: dict[str, Any] | None,
    valid_codes: set[str],
    calibrated_arbitration: bool,
) -> dict[str, Any]:
    if luna is None or not _valid_prediction(luna, valid_codes):
        return dict(jev)
    if not _valid_prediction(jev, valid_codes):
        return {
            "status": "REVIEW_REQUIRED",
            "codes": list(luna["codes"]),
            "reason": "jev_invalid_luna_valid",
        }
    if set(jev["codes"]) == set(luna["codes"]):
        return {
            "status": "AUTO_CODED" if calibrated_arbitration else jev.get("status", "REVIEW_REQUIRED"),
            "codes": list(jev["codes"]),
            "reason": "model_agreement",
        }
    return {
        "status": "REVIEW_REQUIRED",
        "codes": list(jev["codes"]),
        "luna_codes": list(luna["codes"]),
        "reason": "model_disagreement",
    }
