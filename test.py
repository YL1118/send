if __name__ == "__main__":
    raw = """
    受文者：全球人壽保險股份有限公司
    主旨：請協助提供要保人資料
    說明：一、函查對象：張祐綸  身分證字號：A123456789
          二、來文由臺北市政府警察局大安分局轉送
    """
    result = run_full_pipeline(raw)
    print(result)
    # 可能輸出：
    # {'target_name': '張祐綸', 'id_number': 'A123456789', 'agency': '臺北市政府警察局大安分局'}