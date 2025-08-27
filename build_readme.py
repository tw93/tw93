import feedparser
import pathlib
import re
import os
import datetime
from github import Github

root = pathlib.Path(__file__).parent.resolve()


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



def fetch_releases(oauth_token):
    try:
        g = Github(oauth_token)
        user = g.get_user()
        releases = []
        
        # Get all repositories owned by the user
        for repo in user.get_repos(type='owner'):
            if not repo.fork:  # Skip forked repositories
                try:
                    # Get releases for this repository
                    for release in repo.get_releases()[:10]:  # Limit to 10 releases per repo
                        releases.append({
                            "repo": repo.name,
                            "repo_url": repo.html_url,
                            "description": repo.description or "",
                            "release": release.title.replace(repo.name, "").strip(),
                            "published_at": release.published_at.strftime("%Y-%m-%d"),
                            "url": release.html_url,
                        })
                except Exception as e:
                    print(f"Error fetching releases for {repo.name}: {e}")
                    continue
        
        return releases
    except Exception as e:
        print(f"Error fetching releases: {e}")
        return []

def fetch_weekly():
    try:
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
    except Exception as e:
        print(f"Error fetching weekly: {e}")
        return ""


def fetch_blog_entries():
    try:
        entries = feedparser.parse("https://tw93.fun/feed.xml")["entries"]
        return [
            {
                "title": entry["title"],
                "url": entry["link"].split("#")[0],
                "published": entry["published"].split("T")[0],
            }
            for entry in entries
        ]
    except Exception as e:
        print(f"Error fetching blog entries: {e}")
        return []

def fetch_github_stats(oauth_token):
    try:
        g = Github(oauth_token)
        user = g.get_user()
        
        total_stars = 0
        total_forks = 0
        project_count = 0
        
        # Get stats for all owned repos
        for repo in user.get_repos(type='owner'):
            if not repo.fork:  # Skip forked repositories
                total_stars += repo.stargazers_count
                total_forks += repo.forks_count
                project_count += 1
        
        return {
            'stars': total_stars,
            'forks': total_forks, 
            'followers': user.followers,
            'projects': project_count
        }
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
        # Fallback values if API calls fail
        return {
            'stars': 62000,
            'forks': 10000, 
            'followers': 6000,
            'projects': 50
        }


if __name__ == "__main__":
    readme = root / "README.md"
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


    # Combine blog and weekly into one content block
    entries = fetch_blog_entries()[:3]
    blog_md = "<br>".join(
        [
            "• [{title}]({url}) - {published}".format(
                **entry
            )
            for entry in entries
        ]
    ) if entries else ""
    
    weekly_md = fetch_weekly()
    
    # Combine both contents
    if blog_md and weekly_md:
        combined_content = blog_md + "<br>" + weekly_md
    elif blog_md:
        combined_content = blog_md
    elif weekly_md:
        combined_content = weekly_md
    else:
        combined_content = "• No recent posts available"
    
    rewritten = replace_chunk(rewritten, "blog", combined_content)

    readme.open("w").write(rewritten)
