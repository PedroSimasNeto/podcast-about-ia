"""
Gera o roteiro de diálogo (podcast) a partir das notícias coletadas,
    usando um endpoint OpenAI-compatible. Também inclui um passo de auditoria/checagem
que confere se as falas geradas têm respaldo direto no material coletado.
"""

import ast
import json
from datetime import date

from openai import OpenAI

from config import (
    HOST_A,
    HOST_B,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    PODCAST_NAME,
)


def _build_news_block(news_items):
    """Formata as notícias num bloco de texto claro para o prompt."""
    lines = []
    for i, item in enumerate(news_items, start=1):
        lines.append(
            f"[{i}] Fonte: {item['source']}\n"
            f"Título: {item['title']}\n"
            f"Resumo: {item['summary'][:600]}\n"
            f"Link: {item['link']}\n"
        )
    return "\n".join(lines)


def _parse_json_response(raw_text):
    """Interpreta JSON puro e respostas quase-JSON comuns em modelos locais."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as json_error:
        try:
            parsed = ast.literal_eval(cleaned)
        except (SyntaxError, ValueError) as literal_error:
            raise ValueError(
                "O modelo nao retornou um objeto JSON valido. "
                f"Trecho recebido: {cleaned[:300]!r}"
            ) from literal_error
        if not isinstance(parsed, dict):
            raise ValueError("A resposta do modelo nao e um objeto JSON.") from json_error
        return parsed


def generate_script(news_items, client=None):
    """
    Gera o roteiro em formato JSON estruturado:
    {
        "episode_title": str,
        "date": str,
        "dialogue": [{"speaker": str, "text": str, "refs": [int, ...]}, ...],
        "show_notes": [{"title": str, "source": str, "link": str}, ...]
    }

    'refs' aponta para os índices [1], [2]... das notícias usadas naquela fala,
    permitindo checar depois se cada afirmação tem lastro numa fonte real.
    """
    client = client or OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    news_block = _build_news_block(news_items)
    today = date.today().isoformat()

    system_prompt = f"""Você é um roteirista de podcast. Sua tarefa é transformar uma lista de \
notícias sobre Inteligência Artificial em um diálogo natural entre dois apresentadores \
para o podcast "{PODCAST_NAME}".

Apresentadores:
- {HOST_A['name']}: {HOST_A['persona']}
- {HOST_B['name']}: {HOST_B['persona']}

REGRAS IMPORTANTES:
1. Use APENAS as informações fornecidas na lista de notícias abaixo. NUNCA invente fatos, \
números, datas ou declarações que não estejam no material fornecido.
2. Cada notícia tem um índice entre colchetes, ex: [1], [2]. Toda fala que mencionar \
um fato de uma notícia deve registrar esse índice no campo "refs".
3. Escreva como uma conversa real gravada, não como uma lista de notícias. Cada fala deve \
reagir ao que o outro acabou de dizer: concorde, faça uma pergunta de acompanhamento, \
complete uma ideia ou mude de assunto com uma transição natural.
4. Varie o ritmo: alterne falas curtas e médias, use perguntas espontâneas, comentários \
breves e explicações mais completas. Evite que os apresentadores repitam o título da \
notícia ou usem sempre a mesma estrutura de pergunta e resposta.
5. Mantenha os apresentadores humanos e distintos. Diego pode demonstrar surpresa, dúvida \
ou humor leve; Marina pode esclarecer e contextualizar sem transformar cada resposta em \
uma palestra. Use expressões naturais em português falado, mas sem exagerar em gírias, \
interjeições ou reticências.
6. Em geral, cada fala deve ter de uma a três frases e tratar de uma ideia principal. \
Evite parágrafos longos, listas e frases com muitas informações encadeadas, pois o texto \
será narrado em voz alta.
7. Não faça uma fala por notícia obrigatoriamente. Agrupe assuntos relacionados e deixe \
uma notícia render uma troca de duas ou três falas quando isso ajudar a conversa. Cubra \
todas as notícias, mas não force comentários quando o material não sustentar uma reação.
8. Inclua uma abertura curta e calorosa, uma transição entre blocos de assunto e um \
fechamento curto. Não mencione que é um texto gerado por IA nem leia os índices das fontes.
9. Responda APENAS com um JSON válido, sem markdown, sem texto antes ou depois, no formato:

{{
  "episode_title": "string",
  "dialogue": [
    {{"speaker": "{HOST_A['name']}", "text": "...", "refs": [1]}},
    {{"speaker": "{HOST_B['name']}", "text": "...", "refs": []}}
  ]
}}
"""

    user_prompt = f"Data de hoje: {today}\n\nNotícias coletadas:\n\n{news_block}"

    response = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = response.choices[0].message.content or ""

    script = _parse_json_response(raw_text)

    # Monta show notes a partir dos dados que já temos (não depende do LLM
    # para os links, evitando qualquer risco de link inventado).
    show_notes = [
        {"title": item["title"], "source": item["source"], "link": item["link"]}
        for item in news_items
    ]
    script["show_notes"] = show_notes
    script["date"] = today

    return script


def audit_script(script, news_items, client=None):
    """
    Passo de checagem: pede ao modelo para revisar se cada fala com "refs"
    realmente é consistente com o conteúdo da notícia referenciada, e
    reporta divergências. Não corrige automaticamente — apenas sinaliza
    para revisão humana antes da publicação.
    """
    client = client or OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    news_block = _build_news_block(news_items)

    audit_prompt = f"""Você é um auditor de fidelidade factual. Abaixo está uma lista de \
notícias numeradas e um roteiro de podcast em JSON que faz referência a essas notícias via \
"refs".

Sua tarefa: para cada fala do diálogo que tem "refs" não vazio, verifique se o conteúdo da \
fala é consistente com o resumo da(s) notícia(s) referenciada(s). Aponte qualquer fala que:
- afirme algo que não está no resumo da fonte,
- exagere ou distorça um número/fato,
- misture informações de fontes diferentes de forma enganosa.

Responda APENAS com um JSON no formato:
{{
  "issues": [
    {{"speaker": "...", "text_excerpt": "...", "problem": "..."}}
  ],
  "ok": true/false
}}

Se não houver problemas, retorne "issues": [] e "ok": true.

NOTÍCIAS:
{news_block}

ROTEIRO:
{json.dumps(script.get("dialogue", []), ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": audit_prompt}],
    )

    raw_text = response.choices[0].message.content or ""
    return _parse_json_response(raw_text)


if __name__ == "__main__":
    from collector import collect_news
    from dedup import deduplicate_news, rank_and_limit

    news = collect_news()
    deduped = deduplicate_news(news)
    top_news = rank_and_limit(deduped)

    if not top_news:
        print("Nenhuma notícia relevante encontrada hoje.")
    else:
        script = generate_script(top_news)
        print(json.dumps(script, indent=2, ensure_ascii=False))

        audit = audit_script(script, top_news)
        print("\n--- AUDITORIA ---")
        print(json.dumps(audit, indent=2, ensure_ascii=False))
