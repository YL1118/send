# -*- coding: utf-8 -*-
import re
from typing import List, Tuple, Dict, Any

# ========== 0) 你的標籤與機關後綴（自行調整/擴充） ==========

LABELS = {
    'name': ['函查對象','受查人','相對人','當事人','被保險人','要保人','投保人','申請人','被告','受文者'],
    'id':   ['身分證字號','身分證號','統一證號','身分證','ID','身分證件號碼','國民身分證'],
}

# 機關「結尾形式」：越長越先放（避免「法院」先吃掉「地方法院」）
ORG_SUFFIXES = [
    '地方稅務局','地方檢察署','地方法院','金融監督管理委員會','戶政事務所','稽徵所','消防大隊','警察分局',
    '保險股份有限公司','股份有限公司','保險公司','股份有限公司○○分公司','分公司',
    '保險','公司','法院','地檢署','稅捐處','市政府','縣政府','鄉公所','區公所','公所',
    '基金會','協會','銀行','分行','學校','大學','國小','國中','高中','高工','專科',
    '委員會','工作小組','研究中心','社會局','勞工局','稅務局','稅捐局',
    '內政部','教育部','經濟部','交通部','衛生福利部','司法院','行政院','監察院','考試院',
    '署','局','處','科','隊','院','會','部'
]

# ========== 1) Aho-Corasick（若沒有套件就用 regex 聯集） ==========

try:
    import ahocorasick
    def build_aho(words: List[str]):
        A = ahocorasick.Automaton()
        for w in set(words):
            A.add_word(w, w)
        A.make_automaton()
        return A

    def find_labels(text: str, words: List[str]) -> List[Tuple[str,int,int]]:
        """回傳 (命中的字串, start, end)；end 為包含結束 index"""
        A = build_aho(words)
        return [(w, end-len(w)+1, end) for end, w in A.iter(text)]

except Exception:
    def find_labels(text: str, words: List[str]) -> List[Tuple[str,int,int]]:
        """fallback：用 regex alternation；大小約數十個詞時效能仍可接受"""
        # 轉義 + 長詞優先
        pats = sorted([re.escape(w) for w in set(words)], key=len, reverse=True)
        pat = re.compile('|'.join(pats))
        out=[]
        for m in pat.finditer(text):
            out.append((m.group(), m.start(), m.end()-1))
        return out

# ========== 2) 視窗擷取（標籤右側 N 字） ==========

def label_windows(text: str, hits: List[Tuple[str,int,int]], win_right: int=100, win_left: int=0):
    """
    以標籤命中處做視窗，預設只取右側（win_right），也可設定左側視窗（如需）。
    回傳 [{'label':..., 'span':(s,e), 'window': '...'}]
    """
    out=[]
    n=len(text)
    for w, s, e in hits:
        L = max(0, s - win_left)
        R = min(n, e + 1 + win_right)
        out.append({'label': w, 'span': (s,e), 'window': text[L:R]})
    return out

# ========== 3) 無標籤「機關」偵測：後綴驅動，向左擴展 ==========

def build_org_regex(suffixes: List[str]) -> re.Pattern:
    """
    根據後綴清單動態建 regex：
    - 允許機關名中出現：中文、英數、括號、斜線、連字號、點等
    - 以後綴結束（長詞優先）
    - 最長向左擴展 1~30 字（可調）
    """
    # 允許的「機關名內部字元」
    ALLOW_CHARS = r'[\u3400-\u9FFF\w（）()\-/．·\.、&％%：:，,「」《》〈〉／／\s]'
    # 後綴 alternation（長詞先）
    suf_alt = '|'.join(sorted(map(re.escape, suffixes), key=len, reverse=True))
    # 從左側最多取 1~30 個允許字元，貪婪；再接「後綴」；右邊遇到句讀或換行/空白邊界就停
    pat = rf'({ALLOW_CHARS}{{1,30}}(?:{suf_alt}))(?!{ALLOW_CHARS})'
    return re.compile(pat)

ORG_PAT = build_org_regex(ORG_SUFFIXES)

def find_organizations(text: str, max_len: int=64) -> List[Tuple[str,int,int]]:
    """
    從全文找「以後綴結束」的候選機關，傳回 (org_text, start, end)。
    會做基本清理與長度/黑名單過濾。
    """
    cands=[]
    for m in ORG_PAT.finditer(text):
        seg = m.group(1)
        s,e = m.span(1)
        # 清理內部多餘空白
        seg = re.sub(r'\s{2,}', ' ', seg).strip(' ，,、.')
        # 基本過濾
        if len(seg) < 2 or len(seg) > max_len: 
            continue
        # 排除太短或單字後綴（例如只有「科」）
        if seg in {'科','處','局','部','院','會'}:
            continue
        cands.append((seg, s, e))
    # 去重（保留最長）
    cands = sorted(cands, key=lambda x: (x[1], -len(x[0])))
    dedup=[]
    last_end=-1
    for seg,s,e in cands:
        if s >= last_end:
            dedup.append((seg,s,e))
            last_end = e
    return dedup

# ========== 4) 封裝：一次取得三種候選（name/id 有標籤；org 無標籤） ==========

def fast_locate_candidates(text: str,
                           win_right_name: int = 80,
                           win_right_id: int   = 80,
                           scan_sections: Dict[str,str]=None) -> Dict[str, Any]:
    """
    text: 正規化後全文（建議）
    scan_sections: 若只想在特定分段找機關，可傳 {'main_to_desc': '...', 'after_desc': '...'}
    回傳：
      {
        'labels': {
            'name': [{'label','span','window'}, ...],
            'id':   [{'label','span','window'}, ...],
        },
        'org_candidates': [{'text','span'}, ...]
      }
    """
    # 1) 標籤：姓名 / 身分證
    hits_name = find_labels(text, LABELS['name'])
    hits_id   = find_labels(text, LABELS['id'])
    name_windows = label_windows(text, hits_name, win_right=win_right_name)
    id_windows   = label_windows(text, hits_id,   win_right=win_right_id)

    # 2) 機關：用後綴法（可選擇只掃 main_to_desc + after_desc）
    txt_for_org = ''
    if scan_sections:
        txt_for_org = (scan_sections.get('main_to_desc','') + '\n' +
                       scan_sections.get('after_desc',''))
    else:
        txt_for_org = text
    org_spans = find_organizations(txt_for_org)

    return {
        'labels': {'name': name_windows, 'id': id_windows},
        'org_candidates': [{'text': seg, 'span': (s,e)} for seg,s,e in org_spans]
    }