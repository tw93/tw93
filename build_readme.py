from python_graphql_client import GraphqlClient
import feedparser
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
    GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
    dateStr = datetime.datetime.strptime(timestamp, GMT_FORMAT) + datetime.timedelta(
        hours=8
    )
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
    has_next_page = True
    after_cursor = None

    while has_next_page:
        data = client.execute(
            query=repository_query(after_cursor),
            headers={"Authorization": "Bearer {}".format(oauth_token)},
        )
        for repo in data["data"]["viewer"]["repositories"]["nodes"]:
            if repo["releases"]["totalCount"]:
                repos.append(repo)
                # 为每个仓库的所有发布记录创建条目
                for release_node in repo["releases"]["nodes"]:
                    releases.append(
                        {
                            "repo": repo["name"],
                            "repo_url": repo["url"],
                            "description": repo["description"],
                            "release": release_node["name"]
                            .replace(repo["name"], "")
                            .strip(),
                            "published_at": release_node["publishedAt"].split("T")[0],
                            "url": release_node["url"],
                        }
                    )
        has_next_page = data["data"]["viewer"]["repositories"]["pageInfo"][
            "hasNextPage"
        ]
        after_cursor = data["data"]["viewer"]["repositories"]["pageInfo"]["endCursor"]
    return releases

def fetch_weekly():
    content = feedparser.parse("https://weekly.tw93.fun/rss.xml")["entries"]

    entries = [
        "• [{title}]({url}) - {published}".format(
            title=entry["title"],
            url=entry["link"].split("#")[0],
            published=datetime.datetime.strptime(
                entry["published"], "%a, %d %b %Y %H:%M:%S %Z"
            ).strftime("%Y-%m-%d"),
        )
        for entry in content
    ]

    return "<br>".join(entries[:3])


def fetch_blog_entries():
    entries = feedparser.parse("https://tw93.fun/feed.xml")["entries"]
    return [
        {
            "title": entry["title"],
            "url": entry["link"].split("#")[0],
            "published": entry["published"].split("T")[0],
        }
        for entry in entries
    ]

def fetch_github_stats(oauth_token):
    import json
    import subprocess
    
    # Get user info
    user_result = subprocess.run(['gh', 'api', 'user'], 
                                capture_output=True, text=True)
    user_data = json.loads(user_result.stdout)
    
    # Get tw93 owned repos only
    repos_result = subprocess.run(['gh', 'api', 'user/repos', '--paginate'], 
                                 capture_output=True, text=True)
    repos_data = json.loads(repos_result.stdout)
    
    # Filter only tw93 owned repos (not organization repos)
    tw93_repos = [repo for repo in repos_data if not repo['fork'] and repo['owner']['login'] == 'tw93']
    total_stars = sum(repo['stargazers_count'] for repo in tw93_repos)
    total_forks = sum(repo['forks_count'] for repo in tw93_repos)
    
    # Add contributed projects: XRender and WeexUI
    try:
        weexui_result = subprocess.run(['gh', 'api', 'repos/apache/incubator-weex-ui'], 
                                     capture_output=True, text=True)
        weexui_data = json.loads(weexui_result.stdout)
        total_stars += weexui_data['stargazers_count']
        total_forks += weexui_data['forks_count']
    except:
        pass
    
    # Note: XRender seems to be moved or renamed, skip for now
    
    followers = user_data['followers']
    project_count = len(tw93_repos) + 1  # +1 for WeexUI
    
    return {
        'stars': total_stars,
        'forks': total_forks, 
        'followers': followers,
        'projects': project_count
    }


if __name__ == "__main__":
    readme = root / "README.md"
    project_releases = root / "releases.md"
    releases = fetch_releases(TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    md = "<br>".join(
        [
            "• [{repo} {release}]({url}) - {published_at}".format(
                **release
            )
            for release in releases[:6]
        ]
    )
    readme_contents = readme.open().read()
    rewritten = replace_chunk(readme_contents, "recent_releases", md)
    
    # Get GitHub stats
    stats = fetch_github_stats(TOKEN)
    
    stats_text = f"{stats['followers']:,} followers, {stats['stars']:,} stars, {stats['forks']:,} forks"
    rewritten = replace_chunk(rewritten, "github_stats", stats_text, inline=True)

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

    print("fetch_weekly>>>>>>",fetch_weekly())

    weekly_text = fetch_weekly()
    rewritten = replace_chunk(rewritten, "weekly", weekly_text)

    entries = fetch_blog_entries()[:3]
    entries_md = "<br>".join(
        [
            "• [{title}]({url}) - {published}".format(
                **entry
            )
            for entry in entries
        ]
    )
    rewritten = replace_chunk(rewritten, "blog", entries_md)

    readme.open("w").write(rewritten)
