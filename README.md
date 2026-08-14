# Karaoke

Pipeline em Python 3.12 para converter um vídeo em um vídeo de karaokê: extrai o áudio, transcreve a voz com Whisper, isola os vocais com Audio Separator, identifica notas com pYIN/librosa e renderiza as letras e notas sincronizadas no vídeo.

## Requisitos

- Python 3.12.x
- FFmpeg com filtro `ass`/libass disponível no `PATH`
- Dependências Python do projeto

## Instalação

```bash
cd /home/tiagolofi/Documentos/projetos/karaoke
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Uso

```bash
karaoke /caminho/para/video.mp4 --language pt --model small -o resultado-karaoke.mp4
```

Arquivos intermediários ficam em `.karaoke-work/` (ou no diretório definido por `--work-dir`). O resultado usa o vídeo original, com as legendas e a nota MIDI/frequência exibidas no tempo detectado.

## Arquitetura

```text
vídeo → extração de áudio → Whisper → texto ┐
                         └→ Audio Separator → vocais → pYIN/librosa → notas ─┤
                                                                    └→ sincronização → vídeo final
```

> A transcrição é segmentada (frase); para realce palavra-a-palavra seria necessário acrescentar um alinhador forçado, como WhisperX.

## Compatibilidade

O Spleeter não é compatível com Python 3.12 (`Requires-Python: <3.12`) e foi substituído pelo `audio-separator` 0.44.5 com extra `cpu`, que declara suporte a Python 3.12. As versões de Whisper e librosa foram fixadas para instalações reproduzíveis.
