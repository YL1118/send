# -*- coding: utf-8 -*-
import re
import unicodedata
import jieba

# ===================== 1️⃣ 正規化 =====================

def to_halfwidth(s: str) -> str:
    """全形轉半形"""
    res = []
    for ch in s:
        code = ord(ch)
        if code == 0x3000:
            res.append(' ')
        elif 0xFF01 <= code <= 0xFF5E:
            res.append(chr(code - 0xFEE0))
        else:
            res.append(ch)
    return ''.join(res)

# 常見 OCR 誤字修正常數表，可依真實資料擴充
OCR_FIXES = [
    (r'主\s*旨\s*[:：﹕︰⦂]?', '主旨：'),
    (r'說\s*明\s*[:：﹕︰⦂]?', '說明：'),
    (r'身[分份]證', '身分證'),
    (r'Ｏ', 'O'), (r'ｏ', 'o'),
    (r'０', '0'), (r'１', '1'), (r'Ｂ', 'B'), (r'８', '8'),
]

def normalize_text(text: str) -> str:
    """OCR 文正規化 + 移除中文間空格"""
    t = text.replace('\ufeff', '')
    t = unicodedata.normalize('NFC', t)
    t = to_halfwidth(t)
    t = t.replace('﹕', '：').replace('︰', '：').replace('⦂', '：')
    t = t.replace('–', '-').replace('—', '-')
    t = re.sub(r'[ \u00A0]+', ' ', t)  # 合併多空白
    for pat, rep in OCR_FIXES:
        t = re.sub(pat, rep, t)
    # ⭐ 中文間空格移除（核心）
    t = re.sub(r'(?<=\u4e00)\s+(?=\u4e00)', '', t)
    # 清除行尾空白
    t = '\n'.join(line.rstrip() for line in t.splitlines())
    return t.strip()

# ===================== 2️⃣ 分段 =====================

PAT_MAIN = re.compile(r'主\s*旨\s*[：:]', re.IGNORECASE)
PAT_DESC = re.compile(r'說\s*明\s*[：:]', re.IGNORECASE)

def split_sections(text: str):
    """
    輸入：正規化後全文
    輸出：dict 內含三段
    """
    m_main = PAT_MAIN.search(text)
    m_desc = PAT_DESC.search(text, m_main.end() if m_main else 0)

    if not m_main and not m_desc:
        return {'before_main': text, 'main_to_desc': '', 'after_desc': ''}

    if m_main and not m_desc:
        return {
            'before_main': text[:m_main.start()],
            'main_to_desc': text[m_main.end():],
            'after_desc': ''
        }

    if not m_main and m_desc:
        return {
            'before_main': text[:m_desc.start()],
            'main_to_desc': '',
            'after_desc': text[m_desc.end():]
        }

    return {
        'before_main': text[:m_main.start()],
        'main_to_desc': text[m_main.end():m_desc.start()],
        'after_desc': text[m_desc.end():]
    }

# ===================== 3️⃣ jieba 分詞 =====================

def tokenize_sections(sections: dict):
    """
    對三段文字進行 jieba 分詞，回傳 dict
    """
    tokenized = {}
    for key, value in sections.items():
        if not value.strip():
            tokenized[key] = []
            continue
        # 精確模式，保留標點以利規則抽取
        tokens = [tok for tok in jieba.cut(value, cut_all=False)]
        tokenized[key] = tokens
    return tokenized

# ===================== 4️⃣ 主流程 =====================

def preprocess_and_segment(text: str):
    norm = normalize_text(text)
    secs = split_sections(norm)
    toks = tokenize_sections(secs)
    return {'normalized': norm, 'sections': secs, 'tokens': toks}

# ===================== 示範 =====================

if __name__ == "__main__":
    sample = """
    受文者：全球人壽保險股份有限公司
    主    旨 ： 關於 貴公司 XXX 保單資料 ，請 查照。
    說    明：一、依 ○○○ 函。
             二、檢附清單乙份。
    """
    out = preprocess_and_segment(sample)

    print("====== 正規化後全文 ======")
    print(out['normalized'])
    print("\n====== 三段切分 ======")
    for k, v in out['sections'].items():
        print(f"[{k}]\n{v}\n")
    print("====== jieba 分詞結果（main_to_desc 範例）======")
    print(out['tokens']['main_to_desc'])