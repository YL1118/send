# --- fixes & additions ---

# FIX: newline normalization
def normalize_text(s: str) -> List[str]:
    """Normalize and split into lines, preserving line breaks.
    - Halfwidth normalization
    - Normalize newlines \r\n / \r -> \n
    - Collapse spaces per line (not across lines)
    """
    s = to_halfwidth(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")  # FIX
    lines = s.split("\n")
    lines = [re.sub(r"[ \t\u3000]+", " ", line) for line in lines]
    return lines

# NEW: compact OCR-noisy tokens like 'A 1 2 3 . 4 5 6 7 8 9' -> 'A123456789'
_RE_OCR_GAPS = re.compile(r"[ \u3000\.\-_/]+")

def compact_ocr_noise(s: str) -> str:
    return _RE_OCR_GAPS.sub("", s)

# FIX: ID regex to also match spaced/dotted variants, later compact
RE_ID_TW_FUZZY = re.compile(r"[A-Z][\s.\-_/]*?(?:\d[\s.\-_/]*?){9}")
RE_ID_ARC_FUZZY = re.compile(r"[A-Z][\s.\-_/]*?[A-Z][\s.\-_/]*?(?:\d[\s.\-_/]*?){8}")

def tw_id_checksum_ok(code: str) -> bool:
    code = compact_ocr_noise(code).upper()  # FIX normalize first
    if not RE_ID_TW.fullmatch(code):
        return False
    n = LETTER_MAP.get(code[0])
    if n is None:
        return False
    a, b = divmod(n, 10)
    digits = [a, b] + [int(x) for x in code[1:]]
    return sum(d*w for d, w in zip(digits, WEIGHTS_TW_ID)) % 10 == 0

def arc_id_like(code: str) -> bool:
    code = compact_ocr_noise(code).upper()  # FIX normalize first
    return RE_ID_ARC.fullmatch(code) is not None

# NEW: context blacklist around non-person zones (減少姓名誤擊)
CONTEXT_BLACKLIST_NEAR = NAME_BLACKLIST_NEAR | {"傳真", "電話", "TEL", "FAX", "E-MAIL", "Email", "住址", "地址"}

# FIX: name extractor now supports 1–3 given-name chars + honorific stripping
def name_candidates_from_text(line_text: str, surname_singles: Set[str], surname_doubles: Set[str]) -> List[Tuple[str, int]]:
    cands: List[Tuple[str,int]] = []
    text = line_text
    n = len(text)
    sep_set = set(NAME_SEPARATORS)

    def strip_honorific_after(end_idx: int) -> int:
        # 跳過空白/中點後若連著敬稱，返回敬稱前位置
        j = end_idx
        while j < n and text[j] in sep_set:
            j += 1
        for hon in HONORIFICS:
            L = len(hon)
            if j + L <= n and text[j:j+L] == hon:
                return j  # 砍掉敬稱
        return end_idx

    # 嘗試取 1..3 個給名：偏好 2，再 3，再 1（台灣最常見 2）
    def next_given_after(start: int) -> List[Tuple[str, int]]:
        j = start
        while j < n and text[j] in sep_set:
            j += 1
        taken = []
        pos = j
        while j < n and len(taken) < NAME_GIVEN_MAX:
            ch = text[j]
            if RE_CJK.fullmatch(ch):
                taken.append(ch); j += 1
            elif text[j] in sep_set:
                j += 1
            else:
                break
        outs: List[Tuple[str,int]] = []
        for L in (2, 3, 1):  # 偏好順序
            if NAME_GIVEN_MIN <= L <= len(taken):
                end = pos
                # 找到第 L 個 CJK 的實際終點
                cnt, k = 0, pos
                while k < j and cnt < L:
                    if RE_CJK.fullmatch(text[k]): cnt += 1
                    k += 1
                end = k
                end = strip_honorific_after(end)
                g = "".join(taken[:L])
                if g and g not in BIGRAM_BLACKLIST:
                    outs.append((g, pos, end))
        return outs

    doubles_sorted = sorted(surname_doubles, key=len, reverse=True)
    for i in range(n):
        matched = False
        # 先嘗試複姓
        for ds in doubles_sorted:
            L = len(ds)
            if i + L <= n and text[i:i+L] == ds:
                for g, pos, end in next_given_after(i + L):
                    name = ds + g
                    cands.append((name, i))
                matched = True
                break
        if matched:
            continue
        # 再試單姓
        ch = text[i]
        if ch in surname_singles:
            for g, pos, end in next_given_after(i + 1):
                name = ch + g
                cands.append((name, i))
    return cands

# FIX: 在 find_field_candidates_around_label 裡替換 ID 的尋找與正規化
# 片段（僅示意其中一處，左右/下方三個區塊都同理替換）
# 原本:
# for m in re.finditer(r"[A-Z][0-9]{9}|[A-Z]{2}[0-9]{8}", right_seg):
# 改為：
for m in re.finditer(f"(?:{RE_ID_TW_FUZZY.pattern})|(?:{RE_ID_ARC_FUZZY.pattern})", right_seg):
    raw = m.group(0)
    code = compact_ocr_noise(raw).upper()
    fmt = 1.0 if tw_id_checksum_ok(code) or arc_id_like(code) else 0.5
    add_candidate(code, label.col + m.start(), label.line, "same_right", fmt)

# NEW: 降噪懲罰（在 add_candidate 之前或之後套用）
def penalize_non_person_context(value: str, line_text: str) -> float:
    ctx = line_text
    for bad in CONTEXT_BLACKLIST_NEAR:
        if bad in ctx:
            return 0.15  # 懲罰
    return 0.0
# 使用：cand.penalty += penalize_non_person_context(value, lines[line])