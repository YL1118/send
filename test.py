# 假設你已有：
# out = preprocess_and_segment(raw_text)
norm_text  = out['normalized']
sections   = out['sections']   # {'before_main','main_to_desc','after_desc'}

cands = fast_locate_candidates(norm_text, scan_sections=sections)

# cands['labels']['name']  → 每個元素含：label 命中詞、在全文的 span、以及右側 window
# cands['labels']['id']    → 同上
# cands['org_candidates']  → 直接給你機關候選文字與在（拼接後）文本中的 span