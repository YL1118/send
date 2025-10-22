# ===== (Optional) spaCy PERSON gate for names =====
USE_SPACY_PERSON = True           # ← 只要改成 False 就會停用 PERSON 過濾
SPACY_MODEL = "zh_core_web_sm"    # 建議：zh_core_web_trf 準確度更高但較慢

_SPACY_NLP = None  # lazy init
def _init_spacy():
    global _SPACY_NLP
    if not USE_SPACY_PERSON:
        return None
    if _SPACY_NLP is not None:
        return _SPACY_NLP
    try:
        import spacy
        _SPACY_NLP = spacy.load(SPACY_MODEL)
    except Exception:
        _SPACY_NLP = None
    return _SPACY_NLP

def build_person_index(lines: List[str]):
    """
    把每一行跑過 spaCy，蒐集 PERSON span 供快速比對。
    回傳: { line_index: [(start_col, end_col)] }
    """
    nlp = _init_spacy()
    if nlp is None:
        return {}
    idx: Dict[int, List[Tuple[int,int]]] = {}
    for li, line in enumerate(lines):
        doc = nlp(line)
        spans = []
        for ent in getattr(doc, "ents", []):
            # 僅收 PERSON
            if getattr(ent, "label_", "") == "PERSON":
                spans.append((ent.start_char, ent.end_char))
        if spans:
            idx[li] = spans
    return idx

def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return not (a_end <= b_start or b_end <= a_start)

def is_person_span(person_index: Dict[int, List[Tuple[int,int]]], line: int, start: int, end: int) -> bool:
    """
    判斷 (line, start, end) 這個片段是否與 spaCy 的 PERSON span 有交集
    """
    spans = person_index.get(line)
    if not spans:
        return False
    for s, e in spans:
        if _overlap(start, end, s, e):
            return True
    return False