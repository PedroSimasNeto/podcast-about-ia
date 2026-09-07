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
4. Preserve no idioma original todos os nomes próprios de origem estrangeira, especialmente \
nomes de pessoas, empresas, marcas, produtos, modelos, laboratórios e lugares. Não traduza, \
aportuguese, adapte ou substitua nomes como "OpenAI", "Google DeepMind", "Stable Diffusion", \
"ChatGPT", "Llama" ou "Sam Altman". Siglas e termos que funcionam como nomes também devem \
permanecer como na fonte. A frase ao redor deve continuar em português.
5. Escreva para ser falado em voz alta: frases com ritmo variado, pontuação natural e \
palavras simples. Quando um nome estrangeiro aparecer, mantenha sua grafia original para \
que a narração tente dizê-lo em inglês; nunca escreva uma tradução fonética ou uma versão \
aportuguesada do nome.
6. Mantenha os apresentadores humanos e distintos. Diego pode demonstrar surpresa, dúvida, \
curiosidade ou humor leve; Marina pode esclarecer e contextualizar sem transformar cada \
resposta em uma palestra. Use português falado natural, sem bordões repetidos, gírias \
excessivas ou reticências.
7. Faça cada fala nascer da anterior: retome uma palavra ou ideia que o outro acabou de \
mencionar, responda primeiro ao ponto principal e só então avance. Use interrupções leves, \
concordâncias, discordâncias educadas, perguntas espontâneas e pequenas reações. Não faça \
Diego perguntar genericamente "o que isso significa?" em toda notícia, nem faça Marina \
responder sempre com "sim, é verdade".
8. Varie o ritmo: alterne falas curtas e médias, comentários breves e explicações completas. \
Evite repetir títulos, fazer uma sequência de pergunta e resposta ou transformar o episódio \
em uma lista de manchetes. Em geral, cada fala deve ter de uma a três frases e uma ideia \
principal, sem listas ou muitas informações encadeadas.
9. Dê cobertura equilibrada ao conjunto inteiro: mencione todas as notícias fornecidas ao \
menos uma vez, sem deixar que duas notícias sobre o mesmo produto, empresa ou assunto \
ocupem quase todo o episódio. Separe os blocos por tema e dê prioridade a lançamentos, \
novas ideias, impactos concretos e novidades recentes de big techs. Se houver várias \
notícias sobre o mesmo assunto, trate-as como um único bloco e use as demais para variar \
o episódio.
10. Não faça uma fala por notícia obrigatoriamente. Agrupe assuntos relacionados e deixe \
uma notícia render uma troca de duas ou três falas quando isso ajudar a conversa. Cubra \
todo o conjunto com transições naturais, mas não force comentários quando o material não \
sustentar uma reação.
11. Inclua uma abertura curta e calorosa, transições que conectem os assuntos e um fechamento \
curto. Gere no máximo 16 falas, com no máximo duas frases curtas em cada fala. Não mencione \
que é um texto gerado por IA nem leia os índices das fontes.
12. Responda APENAS com um JSON válido, sem markdown, sem texto antes ou depois, no formato:

{{
  "episode_title": "string",
  "dialogue": [
    {{"speaker": "{HOST_A['name']}", "text": "...", "refs": [1]}},
    {{"speaker": "{HOST_B['name']}", "text": "...", "refs": []}}
  ]
}}
"""

    user_prompt = f"Data de hoje: {today}\n\nNotícias coletadas:\n\n{news_block}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=5000,
        response_format={"type": "json_object"},
        messages=messages,
    )

    raw_text = response.choices[0].message.content or ""

    try:
        script = _parse_json_response(raw_text)
    except ValueError:
        # Tenta novamente com uma instrução curta caso um modelo local corte a resposta.
        retry_messages = messages + [
            {
                "role": "user",
                "content": "Retorne novamente o JSON completo, com no maximo 10 falas curtas. "
                "Nao use aspas escapadas com barra invertida fora de strings JSON.",
            }
        ]
        retry_response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=3500,
            response_format={"type": "json_object"},
            messages=retry_messages,
        )
        script = _parse_json_response(
            retry_response.choices[0].message.content or ""
        )

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
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": audit_prompt}],
    )

    raw_text = response.choices[0].message.content or ""
    try:
        return _parse_json_response(raw_text)
    except ValueError as error:
        # A auditoria nao deve impedir que o episodio seja salvo quando o LLM
        # retornar JSON invalido; sinaliza o retorno para revisao manual.
        return {
            "ok": False,
            "issues": [
                {
                    "speaker": "Sistema",
                    "text_excerpt": "",
                    "problem": f"Resposta invalida do auditor: {error}",
                }
            ],
        }


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
