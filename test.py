def name_candidates_from_text(
    line_text: str,
    surname_singles: Set[str],
    surname_doubles: Set[str],
    *,
    line_idx: int,
    person_index: Dict[int, List[Tuple[int,int]]]
) -> List[Tuple[str, int]]:
    """Return list of (name, col) candidates found in a line using surname rules,
       並且（若啟用且有模型）必須與 spaCy PERSON span 有重疊才通過。
    """
    cands: List[Tuple[str,int]] = []
    for m in re.finditer(rf"[{CJK_RANGE}{NAME_SEPARATORS}]{{2,6}}", line_text):
        frag = m.group(0)
        matched = None
        # 先嘗試複姓
        for ds in sorted(surname_doubles, key=len, reverse=True):
            if frag.startswith(ds):
                rest = frag[len(ds):]
                rest = rest.lstrip(NAME_SEPARATORS)
                if  NAME_GIVEN_MIN <= len(rest) <= NAME_GIVEN_MAX and is_cjk(rest):
                    matched = ds + rest
                    break
        if not matched and frag:
            # 再試單姓
            sur = frag[0]
            if sur in surname_singles:
                rest = frag[1:]
                rest = rest.lstrip(NAME_SEPARATORS)
                if NAME_GIVEN_MIN <= len(rest) <= NAME_GIVEN_MAX and is_cjk(rest):
                    matched = sur + rest

        if matched:
            start = m.start()
            end = m.end()
            # ---- PERSON gate: 需要跟 spaCy PERSON 有重疊才收進候選 ----
            if USE_SPACY_PERSON and person_index:
                if not is_person_span(person_index, line_idx, start, end):
                    continue
            cands.append((matched, start))
    return cands