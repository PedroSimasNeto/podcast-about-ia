"""
Coleta notícias dos feeds RSS configurados em config.py,
filtra por janela de tempo e palavras-chave, e retorna uma lista
padronizada de itens de notícia.
"""

import time
from datetime import datetime, timezone, timedelta
import feedparser

from config import RSS_FEEDS, KEYWORDS, LOOKBACK_HOURS
from news_history import filter_unseen


def _entry_datetime(entry):
    """Extrai a data de publicação de uma entrada RSS, com fallback seguro."""
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return None


def _matches_keywords(text, keywords):
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def collect_news(feeds=None, keywords=None, lookback_hours=None):
    """
    Coleta notícias de todos os feeds configurados.

    Retorna uma lista de dicts:
    {
        "title": str,
        "summary": str,
        "link": str,
        "source": str,
        "published": datetime,
    }
    """
    feeds = feeds or RSS_FEEDS
    keywords = keywords or KEYWORDS
    lookback_hours = lookback_hours or LOOKBACK_HOURS
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    collected = []

    for source_name, url in feeds.items():
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[AVISO] Falha ao ler feed '{source_name}': {e}")
            continue

        if feed.bozo and not feed.entries:
            print(f"[AVISO] Feed '{source_name}' parece inválido ou vazio.")
            continue

        for entry in feed.entries:
            published = _entry_datetime(entry)

            # Se não tiver data, mantemos (alguns feeds não populam isso corretamente)
            # mas priorizamos os que têm data dentro da janela.
            if published and published < cutoff:
                continue

            title = entry.get("title", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = summary.strip()
            link = entry.get("link", "").strip()

            combined_text = f"{title} {summary}"

            # Para feeds já específicos de IA (ex: OpenAI Blog), não filtramos por keyword.
            # Para feeds genéricos, exigimos que bata com alguma keyword.
            generic_sources = {
                "Ars Technica",
                "The Verge AI",
                "WIRED AI",
                "IEEE Spectrum AI",
                "Google AI Blog",
                "Hugging Face Blog",
                "arXiv cs.AI",
                "Hacker News (AI)",
            }
            if source_name in generic_sources and not _matches_keywords(combined_text, keywords):
                continue

            if not title or not link:
                continue

            collected.append({
                "title": title,
                "summary": summary,
                "link": link,
                "source": source_name,
                "published": published.isoformat() if published else None,
            })

    return filter_unseen(collected)


if __name__ == "__main__":
    import json
    news = collect_news()
    print(f"Coletadas {len(news)} notícias.")
    print(json.dumps(news[:5], indent=2, ensure_ascii=False))
