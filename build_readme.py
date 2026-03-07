import feedparser
import pathlib
import re
import os
import datetime
from github import Github

root = pathlib.Path(__file__).parent.resolve()


TOKEN = os.environ.get("GH_TOKEN", "")
TITLE_MAX_LEN = 46


def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FAFF"  # symbols and pictographs extended-a
    "\u2600-\u26FF"          # misc symbols
    "\u2700-\u27BF"          # dingbats
    "\uFE0F"                 # variation selector-16
    "\u200D"                 # zero width joiner
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text):
    if not text:
        return ""
    cleaned = EMOJI_RE.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def truncate_middle(text, max_len=TITLE_MAX_LEN):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_len:
        return text

    ellipsis = "..."
    keep_len = max_len - len(ellipsis)
    if keep_len <= 1:
        return text[:max_len]

    left_len = (keep_len + 1) // 2
    right_len = keep_len // 2
    return f"{text[:left_len]}{ellipsis}{text[-right_len:]}"


def parse_entry_date(entry):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.datetime(*parsed[:6]).strftime("%Y-%m-%d")

    for key in ("published", "updated", "date"):
        value = entry.get(key, "")
        if not value:
            continue

        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if match:
            return match.group(0)

        try:
            return datetime.datetime.strptime(
                value, "%a, %d %b %Y %H:%M:%S %Z"
            ).strftime("%Y-%m-%d")
        except Exception:
            continue

    return ""


def normalize_release_title(repo_name, release):
    title = (release.title or "").replace(repo_name, "").strip()
    title = strip_emoji(title)
    if not title:
        title = strip_emoji(release.tag_name or "").strip()
    return title or "Release"



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
                    repo_releases = list(repo.get_releases())
                    if repo_releases:  # Only process if there are releases
                        for release in repo_releases[:10]:  # Limit to 10 releases per repo
                            releases.append({
                                "repo": repo.name,
                                "repo_url": repo.html_url,
                                "description": repo.description or "",
                                "release": normalize_release_title(repo.name, release),
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
        content = feedparser.parse("https://weekly.tw93.fun/en/rss.xml")["entries"]
        entries = []
        for entry in content:
            title = truncate_middle(entry.get("title", ""))
            url = entry.get("link", "").split("#")[0]
            published = parse_entry_date(entry)
            if not (title and url and published):
                continue
            entries.append(
                "• [{title}]({url}) - {published}".format(
                    title=title, url=url, published=published
                )
            )
            if len(entries) >= 3:
                break
        return "<br>".join(entries[:3])
    except Exception as e:
        print(f"Error fetching weekly: {e}")
        return ""


def fetch_blog_entries():
    try:
        entries = feedparser.parse("https://tw93.fun/en/feed.xml")["entries"]
        results = []
        for entry in entries:
            title = truncate_middle(entry.get("title", ""))
            url = entry.get("link", "").split("#")[0]
            published = parse_entry_date(entry)
            if not (title and url and published):
                continue
            results.append({"title": title, "url": url, "published": published})
        return results
    except Exception as e:
        print(f"Error fetching blog entries: {e}")
        return []

def extract_current_stats(readme_content):
    """Extract current stats from README for fallback"""
    import re
    match = re.search(r'(\d{1,3}(?:,\d{3})*) followers, (\d{1,3}(?:,\d{3})*) stars, (\d{1,3}(?:,\d{3})*) forks', readme_content)
    if match:
        return {
            'followers': int(match.group(1).replace(',', '')),
            'stars': int(match.group(2).replace(',', '')),
            'forks': int(match.group(3).replace(',', ''))
        }
    return {'followers': 6000, 'stars': 62000, 'forks': 10000}

def fetch_github_stats(oauth_token, current_stats=None):
    try:
        g = Github(oauth_token)
        user = g.get_user()
        
        total_stars = 0
        total_forks = 0
        
        for repo in user.get_repos(type='owner'):
            if not repo.fork:
                total_stars += repo.stargazers_count
                total_forks += repo.forks_count
        
        try:
            weexui_repo = g.get_repo("apache/incubator-weex-ui")
            total_stars += weexui_repo.stargazers_count
            total_forks += weexui_repo.forks_count
        except Exception as e:
            print(f"Error fetching weex-ui stats: {e}")
        
        try:
            xrender_repo = g.get_repo("alibaba/x-render")
            total_stars += xrender_repo.stargazers_count
            total_forks += xrender_repo.forks_count
        except Exception as e:
            print(f"Error fetching x-render stats: {e}")
        
        return {
            'stars': total_stars,
            'forks': total_forks, 
            'followers': user.followers
        }
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
        return current_stats or {'stars': 62000, 'forks': 10000, 'followers': 6000}


if __name__ == "__main__":
    readme = root / "README.md"
    readme_contents = readme.open().read()
    
    # Extract current stats for fallback
    current_stats = extract_current_stats(readme_contents)
    
    releases = fetch_releases(TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)

    # Keep only the latest release for each repo
    seen_repos = set()
    unique_releases = []
    for release in releases:
        if release["repo"] not in seen_repos:
            seen_repos.add(release["repo"])
            unique_releases.append(release)

    md = "<br>".join(
        [
            "• [{repo} {release}]({url}) - {published_at}".format(
                **release
            )
            for release in unique_releases[:6]
        ]
    )
    rewritten = replace_chunk(readme_contents, "recent_releases", md)
    
    # Get GitHub stats with fallback to current values
    stats = fetch_github_stats(TOKEN, current_stats)
    
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
