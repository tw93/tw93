"""record test code"""

from python_graphql_client import GraphqlClient
import feedparser
import httpx
import json
import pathlib
import re
import os
import datetime


def fetch_weekly():
    content = feedparser.parse("https://weekly.tw93.fun/rss.xml")["entries"]

    entries = [
        "* <a href='{url}' target='_blank'>{title}</a> - {published}".format(
            title=entry["title"],
            url=entry["link"].split("#")[0],
            published=datetime.datetime.strptime(
                entry["published"], "%a, %d %b %Y %H:%M:%S %Z"
            ).strftime("%Y-%m-%d"),
        )
        for entry in content
    ]

    return "\n".join(entries[:5])


print(fetch_weekly())
"""
* <a href='https://weekly.tw93.fun/posts/157-%E5%BC%95%E5%8A%9B%E5%89%A7%E5%9C%BA/' target='_blank'>第157期 - 引力剧场</a> - 2023-12-18
* <a href='https://weekly.tw93.fun/posts/156-%E5%AF%8C%E5%A3%AB%E5%B1%B1%E4%B8%8B/' target='_blank'>第156期 - 富士山下</a> - 2023-12-11
* <a href='https://weekly.tw93.fun/posts/155-%E4%B8%9C%E4%BA%AC%E5%A4%9C%E6%99%AF/' target='_blank'>第155期 - 东京夜景</a> - 2023-12-04
* <a href='https://weekly.tw93.fun/posts/154-%E7%8E%89%E9%B8%9F%E9%9B%86%E7%BE%8E/' target='_blank'>第154期 - 玉鸟集美</a> - 2023-11-20
* <a href='https://weekly.tw93.fun/posts/153-%E9%AB%98%E7%A9%BA%E7%94%BB%E5%AE%B6/' target='_blank'>第153期 - 高空画家</a> - 2023-11-13
"""
