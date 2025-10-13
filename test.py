# ==============================
# Configuration (tweak as needed)
# ==============================
LABELS: Dict[str, List[str]] = {
    "name": ["姓名", "調查人", "申報人"],
    "id_no": ["身分證字號", "身分證統一編號", "身分證", "身分證統編"],
    "ref_date": ["調查日", "申報基準日", "查詢基準日", "查調財產基準日"],
    "batch_id": ["本次調查名單檔"],
    # NEW: 來函機關/發文機關常見標籤（你可再擴充）
    "from_agency": ["來文機關","來函機關","發文機關","主(發)文機關","發文單位","來文單位","主旨機關"]
}

# NEW: 常見「機關/單位」結尾詞（權重高者在前）
ORG_SUFFIXES: Tuple[str, ...] = (
    "地方法院檢察署","地方檢察署","地方法院","高等法院","行政執行署",
    "稅捐稽徵處","國稅局","警察局","分局","分處","分署",
    "監理所","地政事務所","社會局","衛生局",
    "市政府","縣政府","區公所","鄉公所","鎮公所","戶政事務所",
    "金融監督管理委員會","經濟部","內政部","法務部","交通部","衛福部",
    "委員會","管理處","辦公室","基金會","學校","法院","檢察署",
    "公司","分公司","銀行","分行","保險","保險公司",
    "大隊","隊","科","股","室","組","課","中心","機關","單位"
)

# NEW: 與發文/來文語境相關關鍵詞（做 context_bonus）
AGENCY_CONTEXT = {"發文","來文","函","字第","主旨","機關","單位","抄送"}

# ==============================
# Utilities（補強 normalize_text 的跳脫字元）
# ==============================
def normalize_text(s: str) -> List[str]:
    s = to_halfwidth(s).replace("\r\n", "\n").replace("\r", "\n")
    lines = s.split("\n")
    lines = [re.sub(r"[ \t　]+", " ", line) for line in lines]
    return lines

# ==============================
# NEW: 機關候選抽取
# ==============================
RE_CJK_BLOCK = re.compile(rf"[{CJK_RANGE}0-9A-Za-z（）()《》〈〉、．．\.\-／/]+")  # 粗抓片段
RE_AGENCY_TIGHT = re.compile(rf"[{CJK_RANGE}A-Za-z0-9][{CJK_RANGE}A-Za-z0-9／/・\.\-（）()《》、 ]{{0,40}}(?:{'|'.join(map(re.escape, ORG_SUFFIXES))})")

def agency_candidates_from_text(line_text: str) -> List[Tuple[str, int, float]]:
    """
    以結尾詞為主的機關抽取：
    - 先抓寬鬆片段，再以 ORG_SUFFIXES 收斂
    - 依 suffix 重要性給 format_conf 基礎分
    回傳: [(機關名稱, 起始col, 格式信心)]
    """
    cands: List[Tuple[str, int, float]] = []
    for seg in RE_CJK_BLOCK.finditer(line_text):
        chunk = seg.group(0)
        base_col = seg.start()
        for m in RE_AGENCY_TIGHT.finditer(chunk):
            val = m.group(0).strip(" 、，。:：;；")
            if 2 <= len(val) <= 40:
                # 根據 suffix 排名給分（越前面越高）
                fmt = 0.6
                for rank, suf in enumerate(ORG_SUFFIXES, start=1):
                    if val.endswith(suf):
                        fmt = max(fmt, 1.0 - (rank-1)/len(ORG_SUFFIXES)*0.5)  # 0.5~1.0
                        break
                cands.append((val, base_col + m.start(), fmt))
    return cands

# ==============================
# NEW: 在 find_field_candidates_around_label 中支援 from_agency
# ==============================
def find_field_candidates_around_label(field: str, label: LabelHit, lines: List[str],
                                       surname_singles: Set[str], surname_doubles: Set[str]) -> List[Candidate]:
    results: List[Candidate] = []
    label_line_text = lines[label.line]

    def add_candidate(value: str, vcol: int, line: int, dir_key: str, fmt_conf: float) -> None:
        line_delta = line - label.line
        col_delta = abs(vcol - label.col)
        dist = distance_score(label.col, vcol, line_delta)

        # 機關允許稍遠一些，但限制過遠噪音
        if field == "from_agency":
            if abs(line_delta) > 2:  # 最多跨兩行
                return
            if dist < 0.15:
                return
        elif field == "name":
            if line_delta == 0 and col_delta > 14:
                return
            if line_delta != 0 and col_delta > 10:
                return
            if abs(line_delta) > 1 or dist < 0.5:
                return
        else:
            if dist < 0.2:
                return

        dir_prior = DIRECTION_PRIOR.get(dir_key, 0.0)
        # context bonus: 機關若附近有語境詞，+0.1~0.2
        ctx_bonus = 0.0
        if field == "from_agency":
            window = lines[line][max(0, vcol-12): vcol+30]
            if any(k in window for k in AGENCY_CONTEXT):
                ctx_bonus += 0.15

        results.append(Candidate(
            field=field, value=value, line=line, col=vcol,
            label_line=label.line, label_col=label.col, source_label=label.label_text,
            format_conf=fmt_conf, label_conf=1.0 - min(label.distance, 1)*0.5,
            dir_prior=dir_prior, dist_score=dist, context_bonus=ctx_bonus
        ))

    # ---- same line right/left
    right_seg = label_line_text[label.col:label.col+80]
    left_seg  = label_line_text[max(0, label.col-80):label.col]

    if field == "from_agency":
        for val, c, f in agency_candidates_from_text(right_seg):
            add_candidate(val, label.col + c, label.line, "same_right", f)
        for val, c, f in agency_candidates_from_text(left_seg):
            add_candidate(val, c, label.line, "same_left", f)
    elif field == "name":
        for name, c in name_candidates_from_text(right_seg, surname_singles, surname_doubles):
            add_candidate(name, label.col + c, label.line, "same_right", 0.8)
        for name, c in name_candidates_from_text(left_seg, surname_singles, surname_doubles):
            add_candidate(name, c, label.line, "same_left", 0.8)
    elif field == "id_no":
        for m in re.finditer(r"[A-Z][0-9]{9}|[A-Z]{2}[0-9]{8}", right_seg):
            code = m.group(0); fmt = 1.0 if tw_id_checksum_ok(code) or arc_id_like(code) else 0.5
            add_candidate(code, label.col + m.start(), label.line, "same_right", fmt)
        for m in re.finditer(r"[A-Z][0-9]{9}|[A-Z]{2}[0-9]{8}", left_seg):
            code = m.group(0); fmt = 1.0 if tw_id_checksum_ok(code) or arc_id_like(code) else 0.5
            add_candidate(code, m.start(), label.line, "same_left", fmt)
    elif field == "ref_date":
        for pat in DATE_PATTERNS:
            for m in pat.finditer(right_seg):
                iso = parse_iso_date(m.group(0))
                if iso: add_candidate(iso, label.col + m.start(), label.line, "same_right", 1.0)
        for pat in DATE_PATTERNS:
            for m in pat.finditer(left_seg):
                iso = parse_iso_date(m.group(0))
                if iso: add_candidate(iso, m.start(), label.line, "same_left", 1.0)
    elif field == "batch_id":
        for m in RE_BATCH_13.finditer(right_seg):
            add_candidate(m.group(0), label.col + m.start(), label.line, "same_right", 0.9)
        for m in RE_BATCH_13.finditer(left_seg):
            add_candidate(m.group(0), m.start(), label.line, "same_left", 0.9)

    # ---- lines below
    for dl in range(1, MAX_DOWN_LINES + (1 if field=="from_agency" else 0) + 1):
        li = label.line + dl
        if li >= len(lines): break
        tgt = lines[li]
        if field == "from_agency":
            for val, c, f in agency_candidates_from_text(tgt):
                add_candidate(val, c, li, "below", f)
        elif field == "name":
            for name, c in name_candidates_from_text(tgt, surname_singles, surname_doubles):
                add_candidate(name, c, li, "below", 0.8)
        elif field == "id_no":
            for m in re.finditer(r"[A-Z][0-9]{9}|[A-Z]{2}[0-9]{8}", tgt):
                code = m.group(0); fmt = 1.0 if tw_id_checksum_ok(code) or arc_id_like(code) else 0.5
                add_candidate(code, m.start(), li, "below", fmt)
        elif field == "ref_date":
            for pat in DATE_PATTERNS:
                for m in pat.finditer(tgt):
                    iso = parse_iso_date(m.group(0))
                    if iso: add_candidate(iso, m.start(), li, "below", 1.0)
        elif field == "batch_id":
            for m in RE_BATCH_13.finditer(tgt):
                add_candidate(m.group(0), m.start(), li, "below", 0.9)

    return results