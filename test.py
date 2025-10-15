def preprocess_and_segment(text: str):
    norm1 = normalize_text(text)                     # 你既有的正規化
    norm2 = remove_page_marks_and_margin_noise(norm1) # 新增：去分頁行 + 併行 + 去左側雜訊
    secs  = split_sections(norm2)                    # 既有：三段切分
    toks  = tokenize_sections(secs)                  # 既有：jieba 分詞
    return {'normalized': norm2, 'sections': secs, 'tokens': toks}