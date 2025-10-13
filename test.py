# ==============================
# CHG: 產生候選與分組時涵蓋 from_agency
# ==============================
def extract_from_text(text: str, surname_txt_path: Optional[str] = None) -> Dict:
    lines = normalize_text(text)
    surname_singles, surname_doubles = load_surnames_from_txt(surname_txt_path) if surname_txt_path else (set(), set(DEFAULT_DOUBLE_SURNAMES))

    label_hits = find_label_hits(lines, LABELS, max_edit=1)
    per_field_label_presence = {f: False for f in LABELS}
    for h in label_hits:
        per_field_label_presence[h.field] = True

    all_cands: Dict[str, List[Candidate]] = {"name": [], "id_no": [], "ref_date": [], "batch_id": [], "from_agency": []}
    for h in label_hits:
        cands = find_field_candidates_around_label(h.field, h, lines, surname_singles, surname_doubles)
        all_cands[h.field].extend(cands)

    # Anchor assist：若有 ID 但沒 name/agency 標籤，利用 ID 為錨點在近鄰找人名與機關
    if all_cands["id_no"]:
        for idc in all_cands["id_no"]:
            for dl in range(0, MAX_DOWN_LINES + 1):
                li = idc.line + dl
                if li >= len(lines): break
                # name
                if not per_field_label_presence["name"]:
                    for name, col in name_candidates_from_text(lines[li], surname_singles, surname_doubles):
                        dist = distance_score(idc.col, col, li - idc.line)
                        all_cands["name"].append(Candidate(
                            field="name", value=name, line=li, col=col,
                            label_line=idc.label_line, label_col=idc.label_col,
                            source_label=idc.source_label or "(ID-anchored)",
                            format_conf=0.7, label_conf=0.4, dir_prior=0.6, dist_score=dist, context_bonus=0.2
                        ))
                # agency
                if not per_field_label_presence.get("from_agency", False):
                    for val, col, f in agency_candidates_from_text(lines[li]):
                        dist = distance_score(idc.col, col, li - idc.line)
                        all_cands["from_agency"].append(Candidate(
                            field="from_agency", value=val, line=li, col=col,
                            label_line=idc.label_line, label_col=idc.label_col,
                            source_label=idc.source_label or "(ID-anchored)",
                            format_conf=f, label_conf=0.4, dir_prior=0.6, dist_score=dist, context_bonus=0.15
                        ))

    records = group_records(all_cands)

    report: Dict[str, List[str]] = {k: [] for k in ["name","id_no","ref_date","batch_id","from_agency"]}
    for field in report:
        if not per_field_label_presence.get(field, False):
            if all_cands.get(field):
                report[field].append("未找到標籤，但靠近其他錨點找到候選，已打分。")
            else:
                report[field].append("文件中未找到任何該欄位標籤（含模糊匹配）。")
        else:
            if not all_cands.get(field):
                report[field].append("找到了標籤，但其附近未找到符合規則的候選值。")
            else:
                report[field].append(f"找到了標籤與候選（共 {len(all_cands[field])} 條），已根據距離與校驗打分。")

    output = {
        "records": [
            {
                "name": asdict(r.name),
                "id_no": asdict(r.id_no),
                "ref_date": asdict(r.ref_date),
                "batch_id": asdict(r.batch_id),
                # NEW: 輸出 來函機關
                "from_agency": asdict(
                    FieldResult(None,0.0,None,[]))  # 先填預設，稍後在 assemble_record 改
                ,
                "debug": r.debug,
            } for r in records
        ],
        "report": report,
        "meta": { ... }  # 省略（保留你原本內容）
    }
    # 將 assemble_record 產的 agency 寫回（看下方 assemble_record 改動）
    for i, r in enumerate(records):
        output["records"][i]["from_agency"] = asdict(r.debug.get("_from_agency_field", FieldResult(None,0.0,None,[])))
    return output