# Karaoke

Projeto Python 3.12 para gerar vídeos de karaokê e avaliar afinação em tempo real. O pipeline extrai o áudio, transcreve com Whisper, separa voz e instrumental, detecta notas e gera letras sincronizadas em JSON editável. A aplicação em tempo real compara o microfone com o perfil de notas do vídeo escolhido e desenha as letras sobre o vídeo.

## Requisitos

- Python 3.12.x
- FFmpeg disponível no `PATH`
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

Gera o vídeo com instrumental e seus JSONs pareados de auditoria e letras:

```bash
env/bin/karaoke video.mp4 --language pt -o videos/video-pronto-1.mp4
```

O resultado é composto por `videos/video-pronto-1.mp4`, `videos/video-pronto-1.audit.json` e `videos/video-pronto-1.lyrics.json`. O vídeo não contém legenda gravada: o arquivo `.lyrics.json` é editável e o WebApp o carrega em tempo real. Sem `-o`, o destino padrão é `videos/karaoke.mp4`. Os intermediários em `.karaoke-work/` são removidos ao fim da execução bem-sucedida.

### Com modelo e auditoria personalizados

```bash
env/bin/karaoke video.mp4 --language pt --model medium \
  -o "videos/Aonde quer chegar - Turma do Pagode.mp4" \
  --audit-json "videos/Aonde quer chegar - Turma do Pagode.audit.json" \
  --lyrics-json "videos/Aonde quer chegar - Turma do Pagode.lyrics.json"
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
| `-o`, `--output` | `videos/karaoke.mp4` | Caminho do vídeo final, sem legendas gravadas. Os JSONs padrão usam o mesmo nome. |
| `--work-dir` | `.karaoke-work` | Diretório de áudio e stems intermediários. |
| `--models-dir` | `modelos-baixados` | Cache persistente dos modelos de separação; é ignorado pelo Git. |
| `--keep-work-dir` | desativada | Mantém os intermediários ao término; útil para depuração. |
| `--audit-json` | `<vídeo-final>.audit.json` | Define um destino alternativo para o JSON de auditoria. |
| `--lyrics-json` | `<vídeo-final>.lyrics.json` | Define um destino alternativo para o JSON editável das letras. |
| `--model` | `small` | Modelo Faster-Whisper, como `tiny`, `base`, `small`, `medium` ou `large-v3`. |
| `--language` | detecção automática | Idioma ISO-639-1, por exemplo `pt` ou `en`. |
| `-h`, `--help` | — | Exibe a ajuda do comando. |

## WebApp em tempo real

Use fones de ouvido para que o áudio do vídeo não entre no microfone. O pipeline usa o **BS-Roformer Viperx** para separar vocais e instrumental; o modelo é baixado automaticamente na primeira execução. Somente notas que se sobrepõem a uma letra transcrita entram no audit e na melodia de referência. O WebApp exibe uma sidebar com os vídeos da biblioteca, controles de reprodução, volume do vídeo, ganho do microfone, compensação de latência, tolerância e o percentual de acerto no canto. O botão **Ouvir melodia** sintetiza a melodia registrada no audit a partir do ponto atual do vídeo. O botão **Calibrar microfone** mede o ruído ambiente e, ao usar temporariamente os alto-falantes, tenta medir automaticamente a latência pelo tom de teste. A frequência captada no microfone é suavizada por uma mediana de cinco leituras antes de ser convertida em nota, reduzindo erros isolados como classificar um `G` estável como `F#`. A comparação ignora a oitava: por exemplo, `A#2` conta como acerto para uma referência `A#4`. A tolerância padrão é de meio tom, portanto uma referência `G` também aceita `F#` ou `G#`. A nota final usa as amostras de pitch já captadas no navegador e é exibida imediatamente ao término, sem nova gravação nem processamento pesado no backend. A opção **Rufem os tambores** acrescenta uma breve espera sonora antes de revelar o resultado. A aplicação não pontua silêncio ou ruído abaixo do limiar calibrado e aguarda 250 ms no início de cada nota antes de avaliar o feedback.

### Inicializar a aplicação

Abre a biblioteca de vídeos da pasta `videos`:

```bash
env/bin/python karaoke-real-time/app.py
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000) e permita o acesso ao microfone no navegador.

Todo vídeo elegível precisa ter seu arquivo pareado ao lado, como `minha-musica.mp4` e `minha-musica.audit.json`. Para letras editáveis, adicione também `minha-musica.lyrics.json`; o WebApp o sobrepõe ao vídeo. Para compatibilidade com vídeos já processados, se esse arquivo não existir o WebApp usa as letras do audit. Clique em **Atualizar lista** após adicionar novos vídeos.

### Usar biblioteca e servidor personalizados

```bash
env/bin/python karaoke-real-time/app.py --library ./minha-biblioteca \
  --host 127.0.0.1 --port 8080
```

Depois, abra `http://127.0.0.1:8080`. A escolha de vídeo e a tolerância de afinação são feitas pela interface Web.

### Flags da aplicação `karaoke-real-time`

| Flag | Padrão | Descrição |
| --- | --- | --- |
| `--library` | `videos` | Pasta na qual a sidebar busca vídeos e arquivos `.audit.json` e `.lyrics.json` pareados. |
| `--host` | `127.0.0.1` | Endereço do servidor WebApp. |
| `--port` | `8000` | Porta HTTP do servidor. |
| `--reload` | desativada | Reinicia o servidor ao alterar scripts; use apenas em desenvolvimento. |
| `-h`, `--help` | — | Exibe a ajuda do comando. |

## Arquitetura

```text
vídeo → extração de áudio → Whisper → texto → lyrics.json editável ┐
                         └→ Audio Separator → vocais → pYIN/librosa → notas ─┤
                                              └→ instrumental ──────────────────┘
                                                                    └→ vídeo sem legenda + audit.json

microfone → pitch em tempo real → comparação com <vídeo>.audit.json → nota imediata
<vídeo>.lyrics.json → sobreposição de letras no WebApp
```

> A transcrição é segmentada por frase. Para realce palavra a palavra, acrescente um alinhador forçado, como WhisperX.

## Licença e direitos de terceiros

O código original deste repositório é disponibilizado sob a [PolyForm Noncommercial 1.0.0](LICENSE), que não autoriza uso comercial sem permissão do titular dos direitos.

Essa licença cobre somente o código original do projeto. Ela não concede direitos sobre músicas, vídeos, letras, pesos de modelos, nem dependências de terceiros. Antes de distribuir ou usar o projeto comercialmente, obtenha as permissões e confira as licenças aplicáveis a esses materiais.
