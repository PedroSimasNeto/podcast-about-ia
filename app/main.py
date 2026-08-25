"""
Orquestrador do pipeline: coleta -> dedup/ranking -> geração do roteiro
-> auditoria -> salva resultado em disco (JSON + Markdown das show notes).

Uso:
    python main.py

Por padrão, requer o Ollama instalado e o modelo configurado em config.py.
"""

import json
import os
from datetime import date

from collector import collect_news
from dedup import deduplicate_news, rank_and_limit
from script_generator import generate_script, audit_script
from audio_generator import generate_audio
from config import PODCAST_NAME
from news_history import NewsHistory

OUTPUT_DIR = "output"


def save_outputs(script, audit):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = date.today().isoformat()

    json_path = os.path.join(OUTPUT_DIR, f"{today}_episode.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"script": script, "audit": audit}, f, indent=2, ensure_ascii=False)

    # Show notes em Markdown, prontas para publicar
    md_path = os.path.join(OUTPUT_DIR, f"{today}_show_notes.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {PODCAST_NAME} — {script.get('episode_title', today)}\n\n")
        f.write(f"*Episódio de {today}*\n\n")
        f.write("## Roteiro\n\n")
        for line in script.get("dialogue", []):
            f.write(f"**{line['speaker']}:** {line['text']}\n\n")
        f.write("## Fontes\n\n")
        for note in script.get("show_notes", []):
            f.write(f"- [{note['title']}]({note['link']}) — {note['source']}\n")

        if audit and not audit.get("ok", True):
            f.write("\n## ⚠️ Pontos sinalizados pela auditoria (revisar antes de publicar)\n\n")
            for issue in audit.get("issues", []):
                f.write(f"- **{issue['speaker']}**: \"{issue['text_excerpt']}\" — {issue['problem']}\n")

    return json_path, md_path


def run():
    history = NewsHistory()
    history.bootstrap_from_outputs(OUTPUT_DIR)

    print("1/4 Coletando notícias...")
    news = collect_news()
    print(f"   {len(news)} itens brutos coletados.")

    print("2/4 Deduplicando e ranqueando...")
    deduped = deduplicate_news(news)
    top_news = rank_and_limit(deduped)
    print(f"   {len(top_news)} notícias selecionadas para o episódio.")

    if not top_news:
        print("Nenhuma notícia relevante encontrada nas últimas horas. Encerrando.")
        return

    print("3/4 Gerando roteiro do podcast...")
    script = generate_script(top_news)

    print("4/4 Auditando fidelidade factual do roteiro...")
    audit = audit_script(script, top_news)
    if not audit.get("ok", True):
        print(f"   ⚠️  {len(audit.get('issues', []))} ponto(s) sinalizado(s) — revise antes de publicar.")
    else:
        print("   Nenhum problema encontrado na auditoria.")

    json_path, md_path = save_outputs(script, audit)
    print(f"Arquivos salvos em '{OUTPUT_DIR}':\n- {json_path}\n- {md_path}")
    print("5/5 Gerando áudio do episódio...")
    audio_path = generate_audio(json_path)
    history.mark_seen(top_news)
    print(f"\nConcluído. Arquivos gerados:\n- {json_path}\n- {md_path}\n- {audio_path}")


if __name__ == "__main__":
    run()
