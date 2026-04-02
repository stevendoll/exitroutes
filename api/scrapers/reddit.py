"""
Reddit scraper — uses the public JSON API, no auth required.

Searches target subreddits for FieldRoutes complaints.
"""

import json

from api.scrapers.base import BaseScraper
from api.parsers.review_parser import HOT_KEYWORDS, WARM_KEYWORDS

REDDIT_TARGETS = [
    ("pestcontrol",     "fieldroutes"),
    ("pestcontrol",     "service titan"),
    ("smallbusiness",   "fieldroutes"),
    ("lawncare",        "fieldroutes"),
    ("ServiceTitan",    "switch"),
]

REDDIT_API = "https://www.reddit.com/r/{sub}/search.json?q={query}&restrict_sr=1&sort=new&limit=100&t=year"
COMMENTS_API = "https://www.reddit.com/r/{sub}/comments/{post_id}.json?limit=20"

_USER_AGENT = "python:exitroutes-scraper:v1.0 (by /u/exitroutes_app)"


class RedditScraper(BaseScraper):
    source_name = "reddit"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.headers.update({"User-Agent": _USER_AGENT})

    def scrape(self) -> list[dict]:
        results = []
        seen    = set()

        for subreddit, query in REDDIT_TARGETS:
            url  = REDDIT_API.format(sub=subreddit, query=query)
            resp = self.safe_get(url)
            if not resp:
                continue

            try:
                data  = resp.json()
                posts = data.get("data", {}).get("children", [])
            except (json.JSONDecodeError, AttributeError):
                continue

            for post in posts:
                post_data = post.get("data", {})
                post_id   = post_data.get("id", "")

                if post_id in seen:
                    continue
                seen.add(post_id)

                title    = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                combined = f"{title} {selftext}".lower()

                all_keywords = HOT_KEYWORDS + WARM_KEYWORDS
                if not any(k in combined for k in all_keywords):
                    continue

                results.append({
                    "post_id":         post_id,
                    "title":           title,
                    "selftext":        selftext,
                    "author":          post_data.get("author", ""),
                    "subreddit":       post_data.get("subreddit", subreddit),
                    "url":             f"https://reddit.com{post_data.get('permalink', '')}",
                    "created_utc":     post_data.get("created_utc"),
                    "score":           post_data.get("score", 0),
                    "num_comments":    post_data.get("num_comments", 0),
                })

                # Fetch top comments for high-scoring posts
                if post_data.get("score", 0) >= 5 and post_data.get("num_comments", 0) > 0:
                    comments = self._fetch_comments(subreddit, post_id)
                    results.extend(comments)

            self.polite_delay()

        return results

    def _fetch_comments(self, subreddit: str, post_id: str) -> list[dict]:
        url  = COMMENTS_API.format(sub=subreddit, post_id=post_id)
        resp = self.safe_get(url)
        if not resp:
            return []

        results = []
        all_keywords = HOT_KEYWORDS + WARM_KEYWORDS
        try:
            data = resp.json()
            # Reddit returns [post_listing, comments_listing]
            if len(data) < 2:
                return []
            comments = data[1].get("data", {}).get("children", [])
            for c in comments:
                cd   = c.get("data", {})
                body = cd.get("body", "")
                if not body or body == "[deleted]":
                    continue
                if not any(k in body.lower() for k in all_keywords):
                    continue
                results.append({
                    "post_id":     f"{post_id}_comment_{cd.get('id','')}",
                    "title":       "",
                    "selftext":    body,
                    "author":      cd.get("author", ""),
                    "subreddit":   subreddit,
                    "url":         f"https://reddit.com{cd.get('permalink', '')}",
                    "created_utc": cd.get("created_utc"),
                    "score":       cd.get("score", 0),
                    "num_comments": 0,
                })
        except Exception as e:
            self.logger.debug("Comment fetch error: %s", e)

        return results

    def parse_raw(self, raw: dict) -> dict | None:
        text = f"{raw.get('title','')} {raw.get('selftext','')}".strip()
        if not text:
            return None
        return {
            "reviewer_name":    raw.get("author", ""),
            "reviewer_role":    None,
            "company_size":     None,
            "rating":           None,   # Reddit has no star rating
            "cons_text":        text,
            "full_review_text": text,
            "source_url":       raw.get("url", ""),
            "source_id":        raw.get("post_id", ""),
            "business_name":    None,   # unknown for Reddit users
        }
