# 直接抓你在 Graph Explorer 見到的 contentURL
# 例: https://graph.microsoft.com/v1.0/me/onenote/pages/{PAGE_ID}/content?includeIDs=true
CONTENT_URL = "把你找到的 contentURL 貼在這"

CLIENT_ID = "你的 App (client) ID"
TENANT_ID = "你的租戶ID(Directory ID)"  # 企業環境建議不要用 'common'

import msal, requests
from bs4 import BeautifulSoup

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/Notes.Read", "offline_access"]

# 1) 互動式登入拿 token
app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
result = app.acquire_token_interactive(scopes=SCOPES)
if "access_token" not in result:
    raise SystemExit(f"登入失敗：{result.get('error')}, {result.get('error_description')}")
headers = {"Authorization": f"Bearer {result['access_token']}"}

# 2) 直接 GET 你的 contentURL
r = requests.get(CONTENT_URL, headers=headers, timeout=60)
r.raise_for_status()
html = r.text

# 3) 存成 HTML 檔、並轉純文字
with open("onenote_page.html", "w", encoding="utf-8") as f:
    f.write(html)

text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
with open("onenote_page.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("已輸出 onenote_page.html 與 onenote_page.txt（前 300 字預覽）：\n")
print(text[:300])
