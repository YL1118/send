import re, unicodedata

# 廣義中文字判斷（中文間空格清理時會用到）
def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF) or (0xF900 <= o <= 0xFAFF) or (o == 0x3007)

# 分頁線：第2頁，共3頁 / 第3頁, 共3頁
PAGE_MARK_RE = re.compile(r'^\s*第\s*\d+\s*頁\s*[,，、]?\s*共\s*\d+\s*頁\s*$', re.I)

# 變體空白（thin space, 全形空白等）
SPACE_VARIANTS = ''.join(chr(c) for c in list(range(0x2000,0x200B)) + [0x00A0, 0x202F, 0x205F, 0x3000])
# 零寬字元
ZW_SET = {'\u200b','\u200c','\u200d','\ufeff'}
# 各種「點」符號
DOTS_SET = set(['.', '．', '･', '・', '·', '‧', '․', '∙', '⋅', '⸳', '﹒', '｡', '…'])
# 行首常見直排字
MARGIN_WORDS = set(['裝','訂','線'])

def strip_left_margin_prefix(line: str) -> str:
    """
    剝掉行首的「直排雜訊前綴」：空白/零寬 + (點點/裝/訂/線) 反覆出現。
    右邊若還有正文，會被保留下來。
    """
    i, n = 0, len(line)
    removed_any = False
    # 先跳過空白與零寬
    while i < n and (line[i] == ' ' or line[i] in SPACE_VARIANTS or line[i] in ZW_SET):
        i += 1; removed_any = True
    # 再剝掉交錯出現的「點點／裝訂線／空白／零寬」
    while i < n:
        ch = line[i]
        if ch in ZW_SET or ch == ' ' or ch in SPACE_VARIANTS:
            i += 1; removed_any = True
            continue
        if ch in DOTS_SET or ch in MARGIN_WORDS:
            i += 1; removed_any = True
            continue
        break
    # 保留右側內容（避免把真的以「裝訂線」開頭的正文誤刪，這裡已足夠保守）
    return line[i:] if removed_any else line

def remove_page_marks_and_margin_noise(text: str) -> str:
    """
    - 移除分頁線，並把下一行併到上一行（上一行 + 空格 + 下一行）
    - 剝掉每一行左側的雜訊前綴（點點 / 裝訂線 等），保留右側正文
    - 清除中文間多餘空白、零寬字元
    """
    text = text.replace('\ufeff', '')
    text = unicodedata.normalize('NFC', text)
    # 統一奇形空白
    text = re.sub(r'[\u00A0\u2000-\u200A\u202F\u205F\u3000]', ' ', text)

    lines = text.splitlines()
    out = []
    concat_next_to_prev = False

    for raw in lines:
        line = raw.rstrip()

        # 1) 分頁線：丟掉，並把下一行併到上一行
        if PAGE_MARK_RE.match(line):
            concat_next_to_prev = True
            continue

        # 2) 先剝掉左側雜訊前綴，再看要不要併行
        cleaned = strip_left_margin_prefix(line)

        if concat_next_to_prev and out:
            out[-1] = (out[-1].rstrip() + ' ' + cleaned.lstrip()).rstrip()
            concat_next_to_prev = False
        else:
            # 若剝完只剩空白就跳過；否則收進去
            if cleaned.strip():
                out.append(cleaned)

    cleaned_text = '\n'.join(out)

    # 3) 清掉「中文字-空格-中文字」的多餘空格（保留中英/數間空格）
    buf, i = [], 0
    while i < len(cleaned_text):
        ch = cleaned_text[i]
        if ch == ' ' and i > 0 and i+1 < len(cleaned_text) and is_cjk(cleaned_text[i-1]) and is_cjk(cleaned_text[i+1]):
            i += 1
            continue
        if ch in ZW_SET:  # 再保險清一次零寬
            i += 1
            continue
        buf.append(ch); i += 1

    # 4) 合併多空白 → 單一空白；去行尾空白
    final = re.sub(r' {2,}', ' ', ''.join(buf))
    final = '\n'.join(l.rstrip() for l in final.splitlines())
    return final.strip()