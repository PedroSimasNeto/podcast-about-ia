"""
Configurações do bot de podcast de IA.
Edite as listas abaixo para adicionar/remover fontes.
"""

import os

# Feeds RSS de fontes confiáveis sobre IA.
# Adicione ou remova conforme preferir.
RSS_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "MIT Technology Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    "WIRED AI": "https://www.wired.com/feed/tag/ai/latest/rss",
    "IEEE Spectrum AI": "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "OpenAI News": "https://openai.com/news/rss.xml",
    "Google DeepMind Blog": "https://deepmind.google/blog/rss.xml",
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "arXiv cs.AI": "https://export.arxiv.org/rss/cs.AI",
    "Hacker News (AI)": "https://hnrss.org/newest?q=AI",
}

# Palavras-chave para filtrar itens relevantes quando a fonte é genérica
# (ex: Ars Technica cobre vários temas, não só IA).
KEYWORDS = [
    "ai", "inteligência artificial", "llm", "modelo de linguagem",
    "machine learning", "aprendizado de máquina", "gpt", "claude",
    "gemini", "openai", "anthropic", "deepmind", "chatbot", "agente de ia",
    "neural", "transformer",
]

# Quantas notícias no máximo entram no roteiro final (evita episódios gigantes)
MAX_NEWS_ITEMS = 10

# Categorias priorizadas na seleção diária. A ordem também ajuda a equilibrar
# produtos, ideias novas, impactos concretos e movimentos das big techs.
NEWS_TOPIC_PRIORITY = [
    "produto",
    "bigtech",
    "impacto",
    "ideia",
    "negocios",
]

# Quantas horas de "janela" considerar como "notícia de hoje"
LOOKBACK_HOURS = 26  # um pouco mais de 24h pra cobrir fuso/atraso de publicação

# Nomes e personalidades dos apresentadores do podcast
HOST_A = {
    "name": "Marina",
    "persona": "jornalista de tecnologia, analítica, explica contexto e implicações técnicas com clareza",
}
HOST_B = {
    "name": "Diego",
    "persona": "curioso e descontraído, faz perguntas que o público faria, reage com humor leve",
}

# Nome do podcast
PODCAST_NAME = "IA Diária"

# Endpoint e modelo OpenAI-compatible usados na geração do roteiro.
# O padrão roda localmente com Ollama, sem chave ou custo por chamada.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
