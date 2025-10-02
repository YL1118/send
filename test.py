import requests

# Ollama 預設的本機端點
url = "http://localhost:11434/api/chat"

# 選擇要用的模型 (先確認你有 pull 過，比如 "llama3.1" 或 "qwen2")
payload = {
    "model": "llama3.1",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "幫我寫一首關於程式設計的短詩"}
    ],
    "stream": False  # True 表示逐字串流回覆，False 表示整段回來
}

response = requests.post(url, json=payload)

# 印出回覆
if response.status_code == 200:
    data = response.json()
    print("Assistant:", data["message"]["content"])
else:
    print("Error:", response.status_code, response.text)
