import requests
from bs4 import BeautifulSoup

access_token = "YOUR_OAUTH_ACCESS_TOKEN"
headers = {"Authorization": f"Bearer {access_token}"}

# 1) 列頁面
pages = requests.get(
    "https://graph.microsoft.com/v1.0/me/onenote/pages?$top=5",
    headers=headers).json()["value"]

# 2) 抓內容並轉純文字
first_page_id = pages[0]["id"]
html = requests.get(
    f"https://graph.microsoft.com/v1.0/me/onenote/pages/{first_page_id}/content",
    headers=headers).text
text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
print(pages[0]["title"], "\n---\n", text[:1000])
