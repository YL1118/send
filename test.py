import re
import unicodedata

# 1) 判斷廣義中文字（基本區 + Ext-A + 相容表意 + 〇）
def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF) or (0xF900 <= o <= 0xFAFF) or (o == 0x3007)

# 2) 你原本的 normalize_text() 建議在最後再呼叫本函式做進一步清理
PAGE_MARK_RE = re.compile(r'^\s*第\s*\d+\s*頁\s*[,，、]?\s*共\s*\d+\s*頁\s*$', re.I)
DOTS_ONLY_RE = re.compile(r'^[\s\.\u2026\u00B7\u2027\u2219\u30FB\uFF65\u2000-\u200A\u202F\u205F\u3000]+$')  # ., …, ·, ・ 等
LEFT_MARGIN_CHAR_RE = re.compile(r'^[\s\.\u2026\u00B7\u2027\u2219\u30FB\uFF65]*[裝訂線][\s\.\u2026\u00B7\u2027\u2219\u30FB\uFF65]*$')

def remove_page_marks_and_margin_noise(text: str) -> str:
    """
    - 移除 '第2頁，共3頁' / '第3頁, 共3頁' 之類的分頁行，並把下一行併到上一行。
    - 移除左側直排雜訊行（純點點或單獨的「裝/訂/線」等）。
    """
    # 先把奇形空白正規成普通空格（含全形空白）
    text = text.replace('\ufeff', '')
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'[\u00A0\u2000-\u200A\u202F\u205F\u3000]', ' ', text)

    lines = text.splitlines()
    out = []
    concat_next_to_prev = False

    for i, raw in enumerate(lines):
        line = raw.rstrip()

        # ① 分頁行 → 丟掉，並標記下一行要併到上一行
        if PAGE_MARK_RE.match(line):
            concat_next_to_prev = True
            continue

        # ② 左側直排雜訊（純點點 or 單字「裝/訂/線」） → 丟掉
        if DOTS_ONLY_RE.match(line) or LEFT_MARGIN_CHAR_RE.match(line):
            # 這行不要；也不要觸發合併
            continue

        # ③ 真的要輸出的行
        if concat_next_to_prev and out:
            # 把本行併到上一行（留一個空格）
            out[-1] = out[-1].rstrip() + ' ' + line.lstrip()
            concat_next_to_prev = False
        else:
            out.append(line)

    cleaned = '\n'.join(out)

    # ④ 刪掉「中文字-空格-中文字」之間多餘空格（保留中英/數間空格）
    buf, i = [], 0
    while i < len(cleaned):
        ch = cleaned[i]
        if ch == ' ' and i > 0 and i + 1 < len(cleaned) and is_cjk(cleaned[i-1]) and is_cjk(cleaned[i+1]):
            i += 1
            continue
        # 清掉零寬字元
        if ch in ('\u200b', '\u200c', '\u200d'):
            i += 1
            continue
        buf.append(ch)
        i += 1

    # 合併多空白為單一空白、刪尾空白
    final = re.sub(r'[ ]{2,}', ' ', ''.join(buf))
    final = '\n'.join(l.rstrip() for l in final.splitlines())
    return final.strip()