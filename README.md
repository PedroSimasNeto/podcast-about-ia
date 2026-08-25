# IA Diária — Bot de Podcast sobre Notícias de IA

Pipeline que coleta notícias de IA do dia, remove duplicatas, gera um roteiro
de diálogo entre dois apresentadores (simulando um podcast) e audita o
roteiro para garantir que cada afirmação tem lastro nas fontes coletadas.

## Estrutura

```
config.py            # Fontes RSS, palavras-chave, personagens, parâmetros
collector.py          # Coleta notícias via RSS
dedup.py               # Remove duplicatas e ranqueia por relevância
script_generator.py    # Gera o roteiro via LLM OpenAI-compatible + auditoria
main.py                 # Orquestra o pipeline completo
```

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

O padrão usa [Ollama](https://ollama.com/) localmente, sem chave de API e sem custo:

```bash
ollama pull llama3.2:3b
```

Instale e inicie o Ollama antes de rodar `python3 main.py`. O endpoint e o modelo podem
ser configurados por `LLM_BASE_URL`, `LLM_MODEL` e `LLM_API_KEY`. Isso também permite
usar outro provedor OpenAI-compatible com plano gratuito.

Edite `config.py` para:
- adicionar/remover feeds RSS em `RSS_FEEDS`
- ajustar palavras-chave de filtro em `KEYWORDS`
- mudar os nomes/personalidades dos apresentadores (`HOST_A`, `HOST_B`)
- ajustar `MAX_NEWS_ITEMS` (quantas notícias entram no episódio)

## Uso

```bash
python3 main.py
```

Isso vai gerar, dentro de `output/`:
- `AAAA-MM-DD_episode.json` — roteiro completo em JSON (falas + refs às fontes + auditoria)
- `AAAA-MM-DD_show_notes.md` — show notes prontas em Markdown, com links de todas as fontes
- `AAAA-MM-DD_episode.mp3` — episódio em áudio, pronto para enviar como arquivo no WhatsApp

## Testando módulos individualmente

Cada módulo pode ser rodado sozinho para depurar:

```bash
python3 collector.py         # só mostra o que foi coletado
python3 dedup.py              # mostra coleta + deduplicação
python3 script_generator.py   # roda o pipeline completo até a geração do roteiro
```

## Próximos passos sugeridos

1. **Automação diária**: agende `main.py` via cron (Linux/Mac) ou Task Scheduler
   (Windows), ou use GitHub Actions com um workflow agendado (`schedule: cron`).
2. **Áudio**: o `main.py` já converte automaticamente o roteiro JSON em MP3 usando
   `edge-tts`, sem chave de API. É necessário ter `ffmpeg` instalado para o `pydub`.
   Para converter um episódio existente manualmente:
   ```bash
   python3 audio_generator.py output/AAAA-MM-DD_episode.json
   ```
3. **Publicação**: gere um feed RSS de podcast a partir dos episódios (ex: com a
   lib `python-podgen`) ou publique como thread/post automaticamente via API
   da plataforma de sua escolha.
4. **Persistência**: se quiser histórico e evitar reprocessar notícias já usadas
   em episódios anteriores, troque os arquivos JSON por um banco SQLite simples.
5. **Revisão humana**: o campo `audit` no JSON de saída sinaliza falas
   potencialmente problemáticas — vale revisar manualmente antes de publicar,
   especialmente no início, até confiar no pipeline.

## Notas importantes

- O roteiro é gerado com instrução explícita ao modelo de **não inventar fatos**
  além do que está nos resumos coletados, e cada fala carrega referências (`refs`)
  às notícias que a embasam.
- A etapa de auditoria (`audit_script`) roda uma segunda chamada ao modelo,
  agindo como "fact-checker" do próprio roteiro — mas isso **não substitui**
  uma checagem humana antes de publicar algo publicamente.
- Alguns feeds RSS podem mudar de URL ou formato com o tempo; se um feed parar
  de funcionar, o script vai apenas emitir um aviso e seguir com os demais.
