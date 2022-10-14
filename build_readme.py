from python_graphql_client import GraphqlClient
import feedparser
import httpx
import json
import pathlib
import re
import os
import datetime

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")


TOKEN = os.environ.get("GH_TOKEN", "")


def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

def formatGMTime(timestamp):
    GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
    dateStr = datetime.datetime.strptime(timestamp, GMT_FORMAT) + datetime.timedelta(hours=8)
    return dateStr.date()

def repository_query(after_cursor=None):
    return """
query {
  viewer {
    repositories(first: 100, privacy: PUBLIC, isFork:false, ownerAffiliations:OWNER, after:AFTER) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        description
        url
        releases(last: 100, orderBy: { field: CREATED_AT, direction: DESC}) {
          totalCount
          nodes {
            name
            publishedAt
            url
          }
        }
      }
    }
  }
}
""".replace(
        "AFTER", '"{}"'.format(after_cursor) if after_cursor else "null"
    )


def fetch_releases(oauth_token):
    repos = []
    releases = []
    repo_names = set()
    has_next_page = True
    after_cursor = None

    while has_next_page:
        data = client.execute(
            query=repository_query(after_cursor),
            headers={"Authorization": "Bearer {}".format(oauth_token)},
        )
        for repo in data["data"]["viewer"]["repositories"]["nodes"]:
            if repo["releases"]["totalCount"] and repo["name"] not in repo_names:
                repos.append(repo)
                repo_names.add(repo["name"])
                releases.append(
                    {
                        "repo": repo["name"],
                        "repo_url": repo["url"],
                        "description": repo["description"],
                        "release": repo["releases"]["nodes"][0]["name"]
                        .replace(repo["name"], "")
                        .strip(),
                        "published_at": repo["releases"]["nodes"][0][
                            "publishedAt"
                        ].split("T")[0],
                        "url": repo["releases"]["nodes"][0]["url"],
                    }
                )
        has_next_page = data["data"]["viewer"]["repositories"]["pageInfo"][
            "hasNextPage"
        ]
        after_cursor = data["data"]["viewer"]["repositories"]["pageInfo"]["endCursor"]
    return releases


# def fetch_code_time():
#     return httpx.get(
#         "https://gist.githubusercontent.com/tw93/7854aac61f991ef4e7ae7b8440e4fdc6/raw/"
#     )

def fetch_weekly():
    return httpx.get(
        "https://raw.githubusercontent.com/tw93/weekly/main/RECENT.md"
    )

# def fetch_douban():
#     entries = feedparser.parse("https://www.douban.com/feed/people/tangwei93/interests")["entries"]
#     return [
#         {
#             "title": item["title"],
#             "url": item["link"].split("#")[0],
#             "published": formatGMTime(item["published"])
#         }
#         for item in entries
#     ]


def fetch_blog_entries():
    entries = feedparser.parse("https://tw93.github.io/feed.xml")["entries"]
    return [
        {
            "title": entry["title"],
            "url": entry["link"].split("#")[0],
            "published": entry["published"].split("T")[0],
        }
        for entry in entries
    ]


if __name__ == "__main__":
    readme = root / "README.md"
    project_releases = root / "releases.md"
    releases = fetch_releases(TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    md = "\n".join(
        [
            "* <a href='{url}' target='_blank'>{repo} {release}</a> - {published_at}".format(**release)
            for release in releases[:5]
        ]
    )
    readme_contents = readme.open().read()
    rewritten = replace_chunk(readme_contents, "recent_releases", md)

    # Write out full project-releases.md file
    project_releases_md = "\n".join(
        [
            (
                "* **[{repo}]({repo_url})**: [{release}]({url}) - {published_at}\n"
                "<br>{description}"
            ).format(**release)
            for release in releases
        ]
    )
    project_releases_content = project_releases.open().read()
    project_releases_content = replace_chunk(
        project_releases_content, "recent_releases", project_releases_md
    )
    project_releases_content = replace_chunk(
        project_releases_content, "release_count", str(len(releases)), inline=True
    )
    project_releases.open("w").write(project_releases_content)

    # code_time_text = "\n```text\n"+fetch_code_time().text+"\n```\n"

    # rewritten = replace_chunk(rewritten, "code_time", code_time_text)

    # doubans = fetch_douban()[:5]

    # doubans_md = "\n".join(
    #     ["* <a href='{url}' target='_blank'>{title}</a> - {published}".format(**item) for item in doubans]
    # )

    # rewritten = replace_chunk(rewritten, "douban", doubans_md)

    weekly_text = "\n"+fetch_weekly().text
    rewritten = replace_chunk(rewritten, "weekly", weekly_text)

    entries = fetch_blog_entries()[:5]
    entries_md = "\n".join(
        ["* <a href='{url}' target='_blank'>{title}</a> - {published}".format(**entry) for entry in entries]
    )
    rewritten = replace_chunk(rewritten, "blog", entries_md)

    readme.open("w").write(rewritten)
