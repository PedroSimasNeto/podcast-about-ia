"""
Deduplicação simples de notícias por similaridade de título
(usando difflib, sem dependências pesadas) e corte para o
número máximo de itens configurado.
"""

from difflib import SequenceMatcher
from app.config import MAX_NEWS_ITEMS


def _similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


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
    Ranqueia por número de fontes que cobriram o assunto (proxy simples
    de relevância) e corta para o limite configurado.
    """
    max_items = max_items or MAX_NEWS_ITEMS
    ranked = sorted(news_items, key=lambda x: x.get("coverage_count", 1), reverse=True)
    return ranked[:max_items]


if __name__ == "__main__":
    from app.collector import collect_news
    import json

    news = collect_news()
    deduped = deduplicate_news(news)
    top = rank_and_limit(deduped)
    print(f"Antes: {len(news)} | Depois de dedup: {len(deduped)} | Top: {len(top)}")
    print(json.dumps(top, indent=2, ensure_ascii=False))
