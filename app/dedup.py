"""Deduplicação, relevância e seleção diversificada das notícias do episódio."""

from datetime import datetime, timezone
from difflib import SequenceMatcher

from config import MAX_NEWS_ITEMS, NEWS_TOPIC_PRIORITY


TOPIC_KEYWORDS = {
    "produto": (
        "launch", "release", "released", "unveil", "introduces", "feature",
        "app", "tool", "product", "model", "chip", "assistant", "cowork",
    ),
    "bigtech": (
        "openai", "google", "deepmind", "microsoft", "meta", "amazon",
        "apple", "anthropic", "nvidia", "xai", "gemini", "claude",
    ),
    "impacto": (
        "impact", "jobs", "health", "education", "school", "worker", "court",
        "government", "environment", "energy", "society", "safety",
    ),
    "ideia": (
        "agent", "robot", "robotics", "research", "new way", "invention",
        "indexing", "infrastructure", "reasoning", "vision", "voice",
    ),
    "negocios": (
        "funding", "raises", "valuation", "acquires", "acquisition", "backs",
        "investment", "startup", "executive", "company",
    ),
}


def _similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _topics(item):
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return {
        topic for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    } or {"geral"}


def _recency_score(item):
    published = item.get("published")
    if not published:
        return 0
    try:
        age_hours = max(
            0,
            (datetime.now(timezone.utc) - datetime.fromisoformat(published)).total_seconds() / 3600,
        )
    except (TypeError, ValueError):
        return 0
    return max(0, 26 - age_hours) / 26


def _relevance_score(item):
    topics = _topics(item)
    priority_score = sum(
        len(NEWS_TOPIC_PRIORITY) - index
        for index, topic in enumerate(NEWS_TOPIC_PRIORITY)
        if topic in topics
    )
    return priority_score + (item.get("coverage_count", 1) * 0.5) + _recency_score(item) * 3


def deduplicate_news(news_items, similarity_threshold=0.75):
    """
    Agrupa notícias muito parecidas (provavelmente o mesmo fato,
    reportado por fontes diferentes) e mantém apenas uma por grupo,
    guardando as fontes extras como referências adicionais.
    """
    groups = []  # cada grupo é uma lista de itens parecidos

    for item in news_items:
        placed = False
        for group in groups:
            if _similarity(item["title"], group[0]["title"]) >= similarity_threshold:
                group.append(item)
                placed = True
                break
        if not placed:
            groups.append([item])

    deduped = []
    for group in groups:
        primary = group[0]
        # Guarda links extras de outras fontes que cobriram o mesmo assunto
        extra_sources = [
            {"source": g["source"], "link": g["link"]}
            for g in group[1:]
        ]
        primary = dict(primary)
        primary["also_covered_by"] = extra_sources
        primary["coverage_count"] = len(group)
        deduped.append(primary)

    return deduped


def rank_and_limit(news_items, max_items=None):
    """
    Prioriza notícias quentes e relevantes, mas escolhe de forma gulosa para
    cobrir categorias diferentes e evitar que um único tema domine o episódio.
    """
    max_items = max_items or MAX_NEWS_ITEMS
    candidates = sorted(news_items, key=_relevance_score, reverse=True)
    selected = []
    topic_counts = {}

    while candidates and len(selected) < max_items:
        best_index = 0
        best_score = float("-inf")
        for index, item in enumerate(candidates):
            topics = _topics(item)
            repeated_topics = sum(topic_counts.get(topic, 0) for topic in topics)
            source_repetition = sum(
                selected_item.get("source") == item.get("source")
                for selected_item in selected
            )
            score = _relevance_score(item) - (repeated_topics * 2) - (source_repetition * 0.15)
            if score > best_score:
                best_index, best_score = index, score

        item = candidates.pop(best_index)
        selected.append(item)
        for topic in _topics(item):
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    return selected


if __name__ == "__main__":
    from collector import collect_news
    import json

    news = collect_news()
    deduped = deduplicate_news(news)
    top = rank_and_limit(deduped)
    print(f"Antes: {len(news)} | Depois de dedup: {len(deduped)} | Top: {len(top)}")
    print(json.dumps(top, indent=2, ensure_ascii=False))
