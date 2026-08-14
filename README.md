# Karaoke

Projeto Python 3.12 para gerar vídeos de karaokê e avaliar afinação em tempo real. O pipeline extrai o áudio, transcreve com Whisper, separa voz e instrumental, detecta notas e renderiza legendas sincronizadas. A aplicação em tempo real compara o microfone com o perfil de notas do vídeo escolhido.

## Requisitos

- Python 3.12.x
- FFmpeg com filtro `ass`/libass disponível no `PATH`
- PortAudio no sistema para acesso ao microfone (`sudo apt-get install libportaudio2` no Ubuntu/Debian)

## Inicialização

No diretório do projeto, crie/atualize o ambiente e instale todas as dependências:

```bash
cd /home/tiagolofi/Documentos/projetos/karaoke
python3.12 -m venv env
env/bin/python -m pip install --upgrade pip
env/bin/python -m pip install -e ".[dev]"
```

## Uso do pipeline

### Mais simples

Gera um vídeo de karaokê e o seu JSON de auditoria pareado:

```bash
env/bin/karaoke video.mp4 --language pt -o video-pronto-1.mp4
```

O resultado é composto por `video-pronto-1.mp4` e `video-pronto-1.audit.json`. Os intermediários em `.karaoke-work/` são removidos ao fim da execução bem-sucedida.

### Com modelo e auditoria personalizados

```bash
env/bin/karaoke video.mp4 --language pt --model medium \
  -o "Aonde quer chegar - Turma do Pagode.mp4" \
  --audit-json "Aonde quer chegar - Turma do Pagode.audit.json"
```

### Depuração avançada

Preserva os artefatos intermediários e usa uma área de trabalho isolada:

```bash
env/bin/karaoke video.mp4 --language pt --model small \
  --work-dir .karaoke-work-debug --keep-work-dir \
  -o video-debug.mp4
```

### Flags do pipeline `karaoke`

| Flag | Padrão | Descrição |
| --- | --- | --- |
| `video` | — | Caminho do vídeo de entrada. |
| `-o`, `--output` | `karaoke.mp4` | Caminho do vídeo final. O audit padrão usa o mesmo nome com `.audit.json`. |
| `--work-dir` | `.karaoke-work` | Diretório de áudio, stems e legendas intermediários. |
| `--keep-work-dir` | desativada | Mantém os intermediários ao término; útil para depuração. |
| `--audit-json` | `<vídeo-final>.audit.json` | Define um destino alternativo para o JSON de auditoria. |
| `--model` | `small` | Modelo Faster-Whisper, como `tiny`, `base`, `small`, `medium` ou `large-v3`. |
| `--language` | detecção automática | Idioma ISO-639-1, por exemplo `pt` ou `en`. |
| `-h`, `--help` | — | Exibe a ajuda do comando. |

## Aplicação em tempo real

Use fones de ouvido para que o áudio do vídeo não entre no microfone. A janela exibe uma sidebar com os vídeos da biblioteca, controles de reprodução, volume do vídeo, ganho do microfone e o percentual de acerto no canto. Ao fim do vídeo, ela mostra `Sua nota foi: XX.X%`.

### Inicializar a aplicação

Abre a biblioteca de vídeos da pasta atual:

```bash
env/bin/python karaoke-real-time/app.py --library .
```

Todo vídeo elegível precisa ter seu arquivo pareado ao lado, como `minha-musica.mp4` e `minha-musica.audit.json`. Clique em **Atualizar lista** após adicionar novos vídeos.

### Abrir um vídeo específico

```bash
env/bin/python karaoke-real-time/app.py "Aonde quer chegar - Turma do Pagode.mp4"
```

### Usar biblioteca, dispositivo e tolerância personalizados

```bash
env/bin/python karaoke-real-time/app.py --library ./minha-biblioteca \
  --device 1 --tolerance-cents 40
```

### Flags da aplicação `karaoke-real-time`

| Flag | Padrão | Descrição |
| --- | --- | --- |
| `video` | — | Vídeo inicial opcional; a pasta dele se torna a biblioteca. |
| `--library` | pasta atual | Pasta na qual a sidebar busca vídeos. Ignorada quando `video` é informado. |
| `--reference` | `<vídeo>.audit.json` | Arquivo de auditoria alternativo, usado apenas para o vídeo inicial. |
| `--device` | microfone padrão | Índice ou nome do dispositivo de entrada de áudio. |
| `--tolerance-cents` | `50` | Margem máxima de desvio para contar um bloco como afinado. |
| `-h`, `--help` | — | Exibe a ajuda do comando. |

## Arquitetura

```text
vídeo → extração de áudio → Whisper → texto ┐
                         └→ Audio Separator → vocais → pYIN/librosa → notas ─┤
                                              └→ instrumental ──────────────────┘
                                                                    └→ vídeo + audit.json

microfone → pitch em tempo real → comparação com <vídeo>.audit.json → percentual de acerto
```

> A transcrição é segmentada por frase. Para realce palavra a palavra, acrescente um alinhador forçado, como WhisperX.
