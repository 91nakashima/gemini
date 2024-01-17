import requests
import dataclasses
from bs4 import BeautifulSoup
import re
import json
import minify_html
from datetime import datetime
from googleapiclient.discovery import build


from key import NOTION_API_KEY, GOOGLE_CSE_ID, GOOGLE_API_KEY


@dataclasses.dataclass
class NotionPageDict:
    title: str
    pageId: str
    content: str
    url: str


@dataclasses.dataclass
class NotionSearch:
    result: list[NotionPageDict]
    has_more: bool
    next_cursor: str

    def to_dict(self):
        return {
            "result": [r.__dict__ for r in self.result],
            "has_more": self.has_more,
            "next_cursor": self.next_cursor
        }


class Notion:
    def __init__(self):
        self.headers = {
            'Notion-Version': '2022-06-28',
            'Authorization': 'Bearer ' + NOTION_API_KEY,
            'Content-Type': 'application/json',
        }

    def search(self, query: str, start_cursor="", page_size=10, add_contests=True) -> NotionSearch:
        """
        Params
        ---
        query: str
            検索クエリ
        page_size: int
            取得件数
        add_contests: bool
            ページの本文を取得するかどうか

        Returns
        ---
        res: dict
            検索結果
        """
        print(f"「{query}」でNotion内検索...")

        request_json = {
            "query": query,
            "page_size": page_size,
        }
        if start_cursor:
            request_json["start_cursor"] = start_cursor

        response = requests.post(
            "https://api.notion.com/v1/search",
            headers=self.headers,
            json=request_json
        )
        response = response.json()

        result = response["results"]

        res_list = []
        for r in result:
            if r["object"] == "page":
                if r["properties"].get("title"):
                    tmp_title = ''
                    for t in r["properties"]["title"]["title"]:
                        tmp_title += t["plain_text"]

                    tmp_content = ""
                    if add_contests:
                        tmp_content = self.get_page_contents(page_id=r["id"])

                    res_list.append(
                        NotionPageDict
                        (
                            title=tmp_title,
                            pageId=r["id"],
                            content=tmp_content,
                            url=""
                        )
                    )

                if r["properties"].get("URL"):
                    tmp_title = ''
                    try:
                        for t in r["properties"]["名前"]["title"]:
                            tmp_title += t["plain_text"]
                    except Exception:
                        continue
                    res_list.append(
                        NotionPageDict
                        (
                            title=tmp_title,
                            pageId=r["id"],
                            content="",
                            url=r["properties"]["URL"]["url"]
                        )
                    )

        return NotionSearch(
            result=res_list,
            has_more=response["has_more"],
            next_cursor=response.get("next_cursor", "")
        )

    def get_page_contents(self, page_id: str) -> dict:
        if not page_id:
            return NotionSearch(
                result=[],
                has_more=False,
                next_cursor=""
            )
        response = requests.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=self.headers,
        )
        if response.status_code != 200:
            return NotionSearch(
                result=[],
                has_more=False,
                next_cursor=""
            )

        response = response.json()

        result = response["results"]

        res_text = ""

        for r in result:
            text_type = r["type"]
            rich_texts = r.get(text_type).get("rich_text", [])
            for rich_text in rich_texts:
                res_text += rich_text["plain_text"] + "\n"

        return res_text


def get_outer_html(url: str):
    """
    URLからページのouterHTMLを取得する

    Params
    ---
    url: str
        ex: https://www.google.com/

    Returns
    ---
    outerHTML: str
        ex: <html>...</html>
        ex: ''
    """
    if isinstance(url, str) is False:
        return ''
    if url in 'https://example.com':
        return ''
    if not url.startswith('http'):
        return ''

    print('詳細情報取得開始...')

    response = None
    try:
        # URLからページのHTMLを取得
        response = requests.get(url, timeout=10)
    except Exception:
        return ''

    if response is None:
        return ''

    # ステータスコードが正常でない場合はNoneを返すなどのエラーハンドリングを行うことができます
    if response.status_code != 200:
        return ''

    # BeautifulSoupを使ってHTMLをパース
    soup = BeautifulSoup(response.content, 'html.parser')

    # styleタグを全て削除
    for style in soup.find_all('style'):
        style.decompose()
    # scriptタグを全て削除
    for script in soup.find_all('script'):
        script.decompose()
    # linkタグを全て削除
    for link in soup.find_all('link'):
        link.decompose()
    # noscriptタグを全て削除
    for noscript in soup.find_all('noscript'):
        noscript.decompose()
    # pictureタグを全て削除
    for picture in soup.find_all('picture'):
        picture.decompose()
    # classを削除
    for tag in soup.find_all(True):
        tag.attrs = {}

    outer_html = str(soup)
    outer_html = re.sub(r"<!--(.*?)-->", '', outer_html)

    outer_html = minify_html.minify(outer_html, minify_js=True, remove_processing_instructions=True)

    # outerHTMLを取得して返す
    return outer_html


def get_now_date_at_ISO() -> str:
    """
    Get the current date and time in ISO8601 format
    """
    return datetime.now().isoformat()


def get_default_serch(title: str) -> str:
    print(f"「{title}」でgoogle検索を開始...")
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    cse = service.cse()
    res = cse.list(q=title, cx=GOOGLE_CSE_ID, num=10).execute()
    results = res.get("items", [])
    snippets = []
    if len(results) == 0:
        return "No good Google Search Result was found"
    for result in results:
        if "snippet" in result:
            add_dist = {}
            add_dist['link'] = result.get('link', '')
            add_dist['snippet'] = result.get('snippet', '')
            add_dist['title'] = result.get('title', '')
            json_str = json.dumps(add_dist, ensure_ascii=False)
            snippets.append(json_str)
    return " ".join(snippets)
