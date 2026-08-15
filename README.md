# Karaoke

Projeto Python 3.12 para gerar vídeos de karaokê e avaliar afinação em tempo real. O pipeline extrai o áudio, transcreve com Whisper, separa voz e instrumental, detecta notas e renderiza legendas sincronizadas. A aplicação em tempo real compara o microfone com o perfil de notas do vídeo escolhido.

## Requisitos

- Python 3.12.x
- FFmpeg com filtro `ass`/libass disponível no `PATH`
- Um navegador moderno com permissão para usar o microfone

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
env/bin/karaoke video.mp4 --language pt -o videos/video-pronto-1.mp4
```

O resultado é composto por `videos/video-pronto-1.mp4` e `videos/video-pronto-1.audit.json`. Sem `-o`, o destino padrão é `videos/karaoke.mp4`. Os intermediários em `.karaoke-work/` são removidos ao fim da execução bem-sucedida.

### Com modelo e auditoria personalizados

```bash
env/bin/karaoke video.mp4 --language pt --model medium \
  -o "videos/Aonde quer chegar - Turma do Pagode.mp4" \
  --audit-json "videos/Aonde quer chegar - Turma do Pagode.audit.json"
```

### Depuração avançada

Preserva os artefatos intermediários e usa uma área de trabalho isolada:

```bash
env/bin/karaoke video.mp4 --language pt --model small \
  --work-dir .karaoke-work-debug --keep-work-dir \
  -o videos/video-debug.mp4
```

### Flags do pipeline `karaoke`

| Flag | Padrão | Descrição |
| --- | --- | --- |
| `video` | — | Caminho do vídeo de entrada. |
| `-o`, `--output` | `videos/karaoke.mp4` | Caminho do vídeo final. O audit padrão usa o mesmo nome com `.audit.json`. |
| `--work-dir` | `.karaoke-work` | Diretório de áudio, stems e legendas intermediários. |
| `--models-dir` | `modelos-baixados` | Cache persistente dos modelos de separação; é ignorado pelo Git. |
| `--keep-work-dir` | desativada | Mantém os intermediários ao término; útil para depuração. |
| `--audit-json` | `<vídeo-final>.audit.json` | Define um destino alternativo para o JSON de auditoria. |
| `--model` | `small` | Modelo Faster-Whisper, como `tiny`, `base`, `small`, `medium` ou `large-v3`. |
| `--language` | detecção automática | Idioma ISO-639-1, por exemplo `pt` ou `en`. |
| `-h`, `--help` | — | Exibe a ajuda do comando. |

## WebApp em tempo real

Use fones de ouvido para que o áudio do vídeo não entre no microfone. O WebApp exibe uma sidebar com os vídeos da biblioteca, controles de reprodução, volume do vídeo, ganho do microfone e o percentual de acerto no canto. Ao fim do vídeo, ele mostra `Sua nota foi: XX.X%`.

### Inicializar a aplicação

Abre a biblioteca de vídeos da pasta `videos`:

```bash
env/bin/python karaoke-real-time/app.py
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000) e permita o acesso ao microfone no navegador.

Todo vídeo elegível precisa ter seu arquivo pareado ao lado, como `minha-musica.mp4` e `minha-musica.audit.json`. Clique em **Atualizar lista** após adicionar novos vídeos.

### Usar biblioteca e servidor personalizados

```bash
env/bin/python karaoke-real-time/app.py --library ./minha-biblioteca \
  --host 127.0.0.1 --port 8080
```

Depois, abra `http://127.0.0.1:8080`. A escolha de vídeo e a tolerância de afinação são feitas pela interface Web.

### Flags da aplicação `karaoke-real-time`

| Flag | Padrão | Descrição |
| --- | --- | --- |
| `--library` | `videos` | Pasta na qual a sidebar busca vídeos e arquivos `.audit.json` pareados. |
| `--host` | `127.0.0.1` | Endereço do servidor WebApp. |
| `--port` | `8000` | Porta HTTP do servidor. |
| `--reload` | desativada | Reinicia o servidor ao alterar scripts; use apenas em desenvolvimento. |
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
