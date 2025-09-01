DOC_BEHAVIOR = {
    "кръвни изследвания": {"has_diag": False, "has_rx": False},
    "епикриза": {"has_diag": True, "has_rx": True},
    "рецепта": {"has_diag": False, "has_rx": True},
    "разчитане на рентгенова снимка": {"has_diag": True, "has_rx": False},
    "разчитане на ехография / ултразвук": {"has_diag": True, "has_rx": False},
    "разчитане на ямр ядрено-магнитен резонанс": {"has_diag": True, "has_rx": False},
    "разчитане на кт компютърна томография": {"has_diag": True, "has_rx": False},
    "амбулаторен лист": {"has_diag": True, "has_rx": False},
    "направление": {"has_diag": True, "has_rx": True},
    "хистологичен резултат / патология": {"has_diag": True, "has_rx": False},
    "административен документ": {"has_diag": False, "has_rx": False},
    "телк решение": {"has_diag": True, "has_rx": False},
    "ваксинационен картон / сертификат": {"has_diag": False, "has_rx": False},
    "биопсия": {"has_diag": True, "has_rx": False},
    "електрокардиограма": {"has_diag": True, "has_rx": False},
    "електромиография": {"has_diag": True, "has_rx": False},
    "мамография": {"has_diag": True, "has_rx": False},
    "гастроскопия / колонскопия": {"has_diag": True, "has_rx": False},
    "оперативен протокол": {"has_diag": True, "has_rx": True},
    "медицинско заключение / становище": {"has_diag": True, "has_rx": True},
    "сертификат / документ за пътуване": {"has_diag": False, "has_rx": False},
}

def doc_behavior_for(doc_type_obj):
    name = (getattr(doc_type_obj, "safe_translation_getter", lambda *a, **k: "")("name", any_language=True)
            or getattr(doc_type_obj, "name", "")).lower().strip()
    slug = (getattr(doc_type_obj, "slug", "") or "").lower().strip()
    return DOC_BEHAVIOR.get(slug) or DOC_BEHAVIOR.get(name) or {"has_diag": False, "has_rx": False}
