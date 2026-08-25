"""Converte o roteiro JSON do episódio em um arquivo MP3 para compartilhar."""

import asyncio
import json
import os
import sys
import tempfile

import edge_tts
from pydub import AudioSegment

from config import HOST_A, HOST_B


VOICE_BY_SPEAKER = {
    HOST_A["name"]: "pt-BR-FranciscaNeural",
    HOST_B["name"]: "pt-BR-AntonioNeural",
}


async def _synthesize(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_audio(episode_json_path, output_path=None):
    """Gera um MP3 a partir de um arquivo *_episode.json."""
    with open(episode_json_path, encoding="utf-8") as file:
        episode = json.load(file)

    script = episode.get("script", episode)
    dialogue = script.get("dialogue", [])
    if not dialogue:
        raise ValueError("O roteiro não contém falas para sintetizar.")

    output_path = output_path or os.path.splitext(episode_json_path)[0] + ".mp3"
    audio = AudioSegment.empty()

    with tempfile.TemporaryDirectory() as temp_dir:
        for index, line in enumerate(dialogue):
            speaker = line.get("speaker", "")
            text = line.get("text", "").strip()
            if not text:
                continue

            voice = VOICE_BY_SPEAKER.get(speaker, "pt-BR-FranciscaNeural")
            speech_path = os.path.join(temp_dir, f"speech_{index}.mp3")
            asyncio.run(_synthesize(text, voice, speech_path))
            audio += AudioSegment.from_mp3(speech_path)
            audio += AudioSegment.silent(duration=350)

    audio.export(output_path, format="mp3", bitrate="128k")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Uso: python3 audio_generator.py output/AAAA-MM-DD_episode.json [saida.mp3]")
        raise SystemExit(2)

    print(generate_audio(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None))