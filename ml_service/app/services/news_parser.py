import newspaper
import requests
import feedparser


def is_rss(url: str):
    try:

        response = requests.get(url)

        if "xml" in response.headers.get("Content-Type", "") or \
                "<rss" in response.text.lower() or "<feed" in response.text.lower():
            return True
        else:
            return False
    except Exception as e:
        print(str(e))


def parse_html(url: str, limit: int):
    try:
        source = newspaper.build(url, memoize_articles=False)
    except Exception as e:
        print(f"Error: can't access {url}. Details: {str(e)}")
        return

    articles_data = []
    try:
        for article in source.articles[:limit]:
            article.download()
            article.parse()

            articles_data.append({
                "title": article.title,
                "publish_date": article.publish_date,
                "top_image": article.top_image,
                "text": article.text
            })
    except Exception as e:
        print(f"Error during parsing news from {url}. Details: {str(e)}")
        return

    return articles_data


def parse_rss(url: str, limit: int):
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"Error: can't parse {url}. Details: {str(e)}")
        return

    articles_data = []
    try:

        for entry in feed.entries[:limit]:
            link = entry.get("link", "")
            if link:
                article = newspaper.Article(link)
                article.download()
                article.parse()
                articles_data.append({
                    "title": article.title,
                    "publish_date": article.publish_date,
                    "top_image": article.top_image,
                    "text": article.text
                })

    except Exception as e:
        print(f"Error during parsing news from {url}. Details: {str(e)}")
        return

    return articles_data


def parse_news(url: str, limit: int = 30):
    if is_rss(url):
        return parse_rss(url, limit)
    else:
        return parse_html(url, limit)
