# ==============================
# CHG: 分組時把機關也配對到同一筆 record
# ==============================
def group_records(all_cands: Dict[str, List[Candidate]]) -> List[Record]:
    records: List[Record] = []

    def nearest(field: str, anchor: Candidate) -> Optional[Candidate]:
        best, best_s = None, -1.0
        for c in all_cands.get(field, []):
            line_delta = abs(c.line - anchor.line)
            if line_delta > MAX_DOWN_LINES + (1 if field=="from_agency" else 0):
                continue
            dist = distance_score(anchor.col, c.col, c.line - anchor.line)
            s = (dist * 3.0) + (0.3 * c.format_conf) + (0.2 * c.dir_prior) + (0.2 * c.context_bonus) - (0.3 * c.penalty)
            if s > best_s:
                best_s, best = s, c
        return best

    id_anchors = sorted(all_cands.get("id_no", []), key=lambda c: (c.line, c.col))
    if id_anchors:
        for a in id_anchors:
            name_c  = nearest("name", a)
            date_c  = nearest("ref_date", a)
            batch_c = nearest("batch_id", a)
            agen_c  = nearest("from_agency", a)  # NEW
            rec = assemble_record(name_c, a, date_c, batch_c, all_cands, agen_c)  # CHG
            records.append(rec)
    else:
        for a in sorted(all_cands.get("name", []), key=lambda c: (c.line, c.col)):
            id_c   = nearest("id_no", a)
            date_c = nearest("ref_date", a)
            batch_c= nearest("batch_id", a)
            agen_c = nearest("from_agency", a)  # NEW
            rec = assemble_record(a, id_c, date_c, batch_c, all_cands, agen_c)  # CHG
            records.append(rec)

    if not records:
        empty = Record(
            name=FieldResult(None, 0.0, None, ["未偵測到任何姓名候選或身分證號錨點"]),
            id_no=FieldResult(None, 0.0, None, ["未偵測到任何身分證號候選"]),
            ref_date=FieldResult(None, 0.0, None, ["未偵測到任何日期候選"]),
            batch_id=FieldResult(None, 0.0, None, ["未偵測到任何13位名單檔候選"]),
            debug={}
        )
        records.append(empty)
    return records

def assemble_record(name_c: Optional[Candidate], id_c: Optional[Candidate],
                    date_c: Optional[Candidate], batch_c: Optional[Candidate],
                    all_cands: Dict[str, List[Candidate]], agen_c: Optional[Candidate] = None) -> Record:
    def field_result_from_cand(c: Optional[Candidate], fallback_notes: List[str]) -> FieldResult:
        if c is None:
            return FieldResult(None, 0.0, None, fallback_notes)
        return FieldResult(
            value=c.value,
            confidence=max(0.0, min(1.0, c.score()/3.0)),
            source={
                "line": c.line, "col": c.col, "label": c.source_label,
                "label_line": c.label_line, "label_col": c.label_col,
                "score_breakdown": {
                    "label_conf": c.label_conf, "format_conf": c.format_conf,
                    "dist_score": c.dist_score, "dir_prior": c.dir_prior,
                    "context_bonus": c.context_bonus, "penalty": c.penalty
                }
            },
            notes=[],
        )

    name_notes = [] if name_c else ["找不到與標籤鄰近且符合規則的姓名候選。"]
    id_notes   = [] if id_c   else ["找不到與標籤鄰近且符合格式/校驗的身分證號候選。"]
    date_notes = [] if date_c else ["找不到可解析為ISO日期的候選（含民國年轉換）。"]
    batch_notes= [] if batch_c else ["找不到13位名單檔候選。"]
    agen_notes = [] if agen_c else ["找不到來函/發文機關候選。"]

    rec = Record(
        name=field_result_from_cand(name_c, name_notes),
        id_no=field_result_from_cand(id_c, id_notes),
        ref_date=field_result_from_cand(date_c, date_notes),
        batch_id=field_result_from_cand(batch_c, batch_notes),
        debug={"all_candidates_counts": {k: len(v) for k, v in all_cands.items()}}
    )
    # NEW: 把機關欄位塞進 debug，讓上游輸出帶出去
    rec.debug["_from_agency_field"] = field_result_from_cand(agen_c, agen_notes)
    return rec