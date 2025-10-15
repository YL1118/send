# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, List, Tuple

# ========== 0) 輔助：台灣身分證/居留證 驗證 ==========

TW_ID_RE  = re.compile(r'[A-Z][12]\d{8}')
ARC_RE    = re.compile(r'[A-Z]{2}\d{8}')  # 常見 ARC 形態；若有新版規則可再擴
TW_CODE = {'A':10,'B':11,'C':12,'D':13,'E':14,'F':15,'G':16,'H':17,'I':34,'J':18,
           'K':19,'L':20,'M':21,'N':22,'O':35,'P':23,'Q':24,'R':25,'S':26,'T':27,
           'U':28,'V':29,'W':32,'X':30,'Y':31,'Z':33}
WEIGHTS = [1,9,8,7,6,5,4,3,2,1,1]

def valid_tw_id(s: str) -> bool:
    if not re.fullmatch(r'[A-Z][12]\d{8}', s): return False
    n = TW_CODE[s[0]]
    digits = [n//10, n%10] + list(map(int, s[1:]))
    return sum(d*w for d,w in zip(digits, WEIGHTS)) % 10 == 0

# ========== 1) 姓名抽取（視窗→候選→打分） ==========

# 取一個精簡版姓氏表（請自行擴充到全量）
SURNAMES = set(list("趙錢孫李周吳鄭王馮陳褚衛蔣沈韓楊朱秦尤許何呂施張孔曹嚴華金魏陶姜戚謝鄒喻柏水竇章雲蘇潘葛奚范彭郎魯韋昌馬苗鳳花方俞任袁柳酆鮑史唐費廉岑薛雷賀倪湯滕殷羅畢郝鄔安常樂於時傅皮卞齊康伍余元卜顧孟平黃和穆蕭尹姚邵湛汪祁毛禹狄米貝明臧計伏成戴談宋茅龐熊紀舒屈項祝董梁杜阮藍閔席季麻強賈路婁危江童顏郭梅盛林刁鐘徐邱駱高夏蔡田樊胡凌霍虞萬支柯昝管盧莫經房裘繆解應宗丁宣賁鄧郁單杭洪包諸左石崔吉龔程嵇邢滑裴陸榮翁荀羊於甄曲家封芮羿儲靳汲邴糜松井段富巫烏焦巴弓牧隗山谷車侯宓蓬全郗班仰秋仲伊宮寧仇欒暴甘鈄歷戎祖武符劉景詹束龍葉幸司韶郜黎薊薄印宿白懷蒲邰從鄂索咸籍賴卓藺屠蒙池喬陰鬱胥能蒼雙聞莘黨翟譚貢勞逄姬申扶堵冉宰郦雍卻璩桑桂濮牛壽通邊扈燕冀郟浦尚農溫別莊晏柴瞿閻充慕連茹習宦艾魚容向古易慎戈廖庾終暨居衡步都耿滿弘匡國文寇廣祿闕東歐殳沃利蔚越夔隆師鞏厙聶晁勾敖融冷訾辛闞那簡饒曾鞠翟開甯尚和南宮司馬歐陽夏侯諸葛上官司徒司空端木獨孤南門東門西門皇甫公孫長孫太叔申屠呼延慕容宇文司馬"))  # 含複姓若干

TITLES = {'先生','小姐','女士','君','同學','股長','經理','主任','科長','上訴人','被告','原告','被保險人','要保人','投保人'}

STOP_CHARS = set('，,。.;；：:（）()《》〈〉「」『』[]【】、 \t\n')

def find_name_candidates_from_window(window: str, max_len: int = 6) -> List[Tuple[str,int]]:
    """
    從標籤右側視窗抓姓名候選（回傳 (name, offset_in_window)）
    規則：
      - 以姓氏起頭（1-2字）
      - 後接名（1-2字），總長 2~4 字（保守）
      - 遇到稱謂詞則剔除稱謂本身
      - 碰到標點/括號等視為邊界
    """
    cands=[]
    n=len(window)
    i=0
    while i < n:
        ch = window[i]
        if ch in SURNAMES:
            # 嘗試 1 或 2 字姓
            for sx in (2,1):
                if i+sx <= n and window[i:i+sx] in SURNAMES:
                    # 名 1~2 字
                    for gx in (2,1):
                        j = i+sx+gx
                        if j <= n:
                            name = window[i:i+sx+gx]
                            # 邊界檢查：前後不得是漢字連續的一部分（用標點或空白切）
                            prev_ok = (i == 0) or (window[i-1] in STOP_CHARS)
                            next_ok = (j == n) or (window[j] in STOP_CHARS)
                            if 2 <= len(name) <= 4 and prev_ok and next_ok:
                                # 剔除稱謂附著：如「張三先生」→取「張三」
                                base = name
                                for t in TITLES:
                                    if base.endswith(t) and 2 <= len(base[:-len(t)]) <= 4:
                                        base = base[:-len(t)]
                                # 避免全是機關後綴字
                                if base and base not in TITLES:
                                    cands.append((base, i))
        i += 1
    # 去重：同一位置選最長
    cands.sort(key=lambda x: (x[1], -len(x[0])))
    out=[]
    used=set()
    for name, off in cands:
        if off not in used:
            out.append((name, off))
            used.add(off)
    return out

def pick_best_name(label_windows: List[Dict[str,Any]]) -> str:
    """
    多個標籤視窗中挑姓名：
    - 分數 = 近距優先（offset 小） + 長度偏好（3字≈2/4字） + 視窗優先級
    """
    best, best_score = '', -1e9
    for rank, item in enumerate(label_windows):
        win = item['window']
        cands = find_name_candidates_from_window(win)
        for name, off in cands:
            # 3字最常見，其次2/4；距離越近分越高；較早命中之標籤稍加分
            len_bonus = {2:0.8, 3:1.0, 4:0.7}.get(len(name), 0.5)
            score = 100/(1+off) + 5*len_bonus + 2*(len(label_windows)-rank)
            if score > best_score:
                best, best_score = name, score
    return best

# ========== 2) 身分證抽取（視窗→驗證→挑最佳） ==========

def find_ids_from_window(window: str) -> List[Tuple[str,int]]:
    """回傳合法 ID 候選 (id_text, offset)；TW 需通過檢查碼，ARC 只做樣式驗證"""
    cands=[]
    for m in TW_ID_RE.finditer(window):
        s = m.group()
        if valid_tw_id(s):
            cands.append((s, m.start()))
    for m in ARC_RE.finditer(window):
        cands.append((m.group(), m.start()))
    # 去重（同值取最近）
    seen=set(); out=[]
    for s,off in sorted(cands, key=lambda x: x[1]):
        if s not in seen:
            out.append((s,off)); seen.add(s)
    return out

def pick_best_id(label_windows: List[Dict[str,Any]]) -> str:
    best, best_score = '', -1e9
    for rank, item in enumerate(label_windows):
        win = item['window']
        cands = find_ids_from_window(win)
        for idv, off in cands:
            score = 200/(1+off) + 2*(len(label_windows)-rank)
            # TW 身分證比 ARC 優先
            if re.fullmatch(r'[A-Z][12]\d{8}', idv):
                score += 50
            if score > best_score:
                best, best_score = idv, score
    return best

# ========== 3) 機關挑選（候選→清理→打分） ==========

ORG_BLACKLIST = {'先生','小姐','女士','同學','股長','經理','主任','科長'}  # 若誤入機關候選則剔除
ORG_SUFFIX_WEIGHT = {
    # 後綴權重（越專業越高），可依你的清單調整
    '金融監督管理委員會': 8, '地方法院': 7, '地方檢察署': 7, '地方稅務局': 7, '戶政事務所': 7,
    '保險股份有限公司': 7, '股份有限公司': 6, '銀行分行': 6, '分行': 5,
    '市政府': 6, '縣政府': 6, '區公所': 5, '鄉公所': 5, '法院': 5, '地檢署': 5,
    '基金會': 4, '協會': 4, '銀行': 4, '公司': 4,
    '部': 2, '署': 2, '局': 2, '處': 2, '科': 1, '隊': 1, '院': 3, '會': 2
}

def clean_org_text(s: str) -> str:
    # 去兩端標點與多空白
    s = re.sub(r'\s+', ' ', s).strip(' ，,、.。/／')
    # 移除不應該在機關名末尾的符號
    s = re.sub(r'[，,、.。/／]+$', '', s).strip()
    return s

def suffix_weight(s: str) -> int:
    for k,v in sorted(ORG_SUFFIX_WEIGHT.items(), key=lambda x: len(x[0]), reverse=True):
        if s.endswith(k):
            return v
    return 0

def pick_best_org(org_candidates: List[Dict[str,Any]]) -> str:
    """
    打分因素：
      - 後綴權重（越專業越高）
      - 名稱長度（適中加分）
      - 內含標點少（乾淨加分）
      - 黑名單過濾
    """
    best, best_score = '', -1e9
    for item in org_candidates:
        raw = item['text']
        org = clean_org_text(raw)
        if not org or any(bad in org for bad in ORG_BLACKLIST):
            continue
        w = suffix_weight(org)
        # 基本長度分（8~18字最佳）
        L = len(org)
        len_score = 5 - abs(13 - min(max(L, 2), 26)) * 0.3
        # 標點罰分
        punct_penalty = sum(1 for ch in org if ch in '，,、.。/／:：')
        score = 10*w + len_score - 0.5*punct_penalty
        if score > best_score:
            best, best_score = org, score
    return best

# ========== 4) 封裝主函式 ==========

def extract_fields(preproc_output: Dict[str,Any],
                   candidates: Dict[str,Any]) -> Dict[str,str]:
    """
    preproc_output: 你 preprocess_and_segment() 的回傳
    candidates:     fast_locate_candidates() 的回傳
    """
    name = pick_best_name(candidates['labels']['name'])
    idno = pick_best_id(candidates['labels']['id'])
    org  = pick_best_org(candidates['org_candidates'])
    return {'target_name': name or '', 'id_number': idno or '', 'agency': org or ''}

# ========== 5) 一鍵流程（若你想從原始文字直接到結果） ==========

def run_full_pipeline(raw_text: str) -> Dict[str,str]:
    """
    假設你已定義：
      - normalize_text
      - remove_page_marks_and_margin_noise
      - split_sections
      - fast_locate_candidates
    """
    norm1 = normalize_text(raw_text)
    norm2 = remove_page_marks_and_margin_noise(norm1)
    secs  = split_sections(norm2)
    # 分詞不是必要，但如果你後面規則會用到 tokens，可以在這裡產出
    # toks  = tokenize_sections(secs)

    cands = fast_locate_candidates(norm2, scan_sections=secs)
    return extract_fields({'normalized': norm2, 'sections': secs}, cands)