# pip install msal requests beautifulsoup4
import time, random
import msal, requests
from bs4 import BeautifulSoup

CLIENT_ID = "你的應用程式(用戶端)ID"
TENANT = "common"  # 個人/多租戶可用 "common"；企業限定可填租戶ID
SCOPES = ["Notes.Read", "offline_access"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"

app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

def acquire_token():
    # 1) 先從快取撈
    accts = app.get_accounts()
    if accts:
        result = app.acquire_token_silent(SCOPES, account=accts[0])
        if result and "access_token" in result:
            return result["access_token"]
    # 2) 裝置碼流程（命令列顯示一段碼，去瀏覽器輸入）
    flow = app.initiate_device_flow(scopes=[f"https://graph.microsoft.com/.default"])
    # 若你的應用 permissions 不是在 .default，改用 SCOPES： initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Device flow 啟動失敗")
    print("請在瀏覽器開啟下列網址並輸入代碼完成登入：")
    print(flow["verification_uri"])
    print("代碼：", flow["user_code"])
    result = app.acquire_token_by_device_flow(flow)  # 會阻塞直到完成或逾時
    if "access_token" not in result:
        raise RuntimeError(f"取得 token 失敗：{result.get('error_description')}")
    return result["access_token"]

def graph_get(url, headers, params=None, max_retries=5):
    for i in range(max_retries):
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 429:
            # 節流：讀 Retry-After，若為 0/缺省，退避 30~60s（含抖動）
            wait = int(r.headers.get("Retry-After", "0"))
            if wait <= 0: wait = random.randint(30, 60)
            time.sleep(wait * (1.5 ** i))  # 漸進退避
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("多次 429 後仍失敗")

token = acquire_token()
headers = {"Authorization": f"Bearer {token}"}

# 1) 列出最近 10 頁（可用 $top / $search）
pages_url = "https://graph.microsoft.com/v1.0/me/onenote/pages"
resp = graph_get(pages_url, headers, params={"$top": 10})
pages = resp.json()["value"]

print(f"抓到 {len(pages)} 頁：")
for p in pages:
    print("-", p.get("title"), p.get("id"))

# 2) 取第一頁 HTML 內容 → 轉純文字
first_id = pages[0]["id"]
content_url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{first_id}/content"
html = graph_get(content_url, headers).text  # 回應為 HTML（XHTML）
text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
print("\n--- 純文字預覽 ---\n", text[:1200])

# 3) 範例：全文搜尋（標題/內容）
search_resp = graph_get(pages_url, headers, params={"$search": "期中報告 OR 簡報"})
hits = search_resp.json().get("value", [])
print(f"\n搜尋命中：{len(hits)}")
for p in hits[:5]:
    print("•", p["title"])
