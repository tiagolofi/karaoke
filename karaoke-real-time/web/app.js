const video = document.querySelector('#video');
const videos = document.querySelector('#videos');
const scoreBox = document.querySelector('#score');
const feedback = document.querySelector('#feedback');
const lyricOverlay = document.querySelector('#lyrics');
const status = document.querySelector('#status');
const play = document.querySelector('#play');
const playMelody = document.querySelector('#play-melody');
const result = document.querySelector('#result');
const calibration = document.querySelector('#calibration');
const calibrationTitle = document.querySelector('#calibration-title');
const calibrationText = document.querySelector('#calibration-text');
const closeCalibration = document.querySelector('#close-calibration');
const calibrateMicrophone = document.querySelector('#calibrate-microphone');
const reset = document.querySelector('#reset');
const micLatency = document.querySelector('#mic-latency');
const micLatencyValue = document.querySelector('#mic-latency-value');
const tolerance = document.querySelector('#tolerance');
const toleranceValue = document.querySelector('#tolerance-value');
const analysisInterval = document.querySelector('#analysis-interval');
const analysisIntervalValue = document.querySelector('#analysis-interval-value');
const PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

let reference = [];
let lyrics = [];
let microphone;
let analyser;
let microphoneGain;
let stream;
let melodyContext;
let melodyNodes = [];
let performanceFrames = [];
let lastPerformanceFrameTime = -Infinity;
let lastLiveScoreTime = -Infinity;
let pitchHistory = [];
let silenceThreshold = 0.015;
const NOTE_START_WINDOW_SECONDS = 0.25;
let analysisFrameIntervalSeconds = 0.12;
const MAX_ANALYSIS_FRAMES = 2500;

function referenceAt(time) { return reference.find((item) => item.start <= time && time <= item.end && item.hz > 0); }
function updateLyrics() {
  const lyric = lyrics.find((item) => item.start <= video.currentTime && video.currentTime <= item.end);
  lyricOverlay.textContent = lyric?.text || '';
}
function pitchClassDistance(first, second) {
  const difference = Math.abs(first - second) % 12;
  return Math.min(difference, 12 - difference);
}
function toleranceLabel(halfSteps) {
  if (halfSteps === 0) return 'sem tolerância';
  if (halfSteps === 1) return '½ tom';
  if (halfSteps === 2) return '1 tom';
  return `${halfSteps / 2}`.replace('.', ',') + ' tons';
}
function rms(buffer) {
  return Math.sqrt(buffer.reduce((sum, sample) => sum + sample * sample, 0) / buffer.length);
}
function sampleMicrophone() {
  const buffer = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(buffer);
  return { buffer, level: rms(buffer) };
}
function wait(milliseconds) { return new Promise((resolve) => window.setTimeout(resolve, milliseconds)); }
function median(values) {
  const ordered = [...values].sort((first, second) => first - second);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
}
function smoothPitch(frequency, history) {
  if (!Number.isFinite(frequency) || frequency <= 0) {
    history.length = 0;
    return null;
  }
  history.push(frequency);
  if (history.length > 5) history.shift();
  return median(history);
}
function compactSequence(sequence) {
  if (sequence.length <= MAX_ANALYSIS_FRAMES) return sequence;
  const step = sequence.length / MAX_ANALYSIS_FRAMES;
  return Array.from({ length: MAX_ANALYSIS_FRAMES }, (_, index) => sequence[Math.floor(index * step)]);
}

function noteFromFrequency(hz) {
  if (!Number.isFinite(hz) || hz <= 0) return null;
  const midi = Math.round(69 + 12 * Math.log2(hz / 440));
  const pitchClassIndex = ((midi % 12) + 12) % 12;
  return { midi, pitchClassIndex, pitchClass: PITCH_CLASSES[pitchClassIndex], name: `${PITCH_CLASSES[pitchClassIndex]}${Math.floor(midi / 12) - 1}` };
}

function midiToFrequency(midi) { return 440 * 2 ** ((midi - 69) / 12); }
function updateMelodyButton() {
  playMelody.textContent = melodyNodes.length ? '■ Parar melodia' : '♪ Ouvir melodia';
}
function stopMelody() {
  melodyNodes.forEach(({ oscillator, gain }) => {
    try { oscillator.stop(); } catch { /* o oscilador já terminou */ }
    oscillator.disconnect();
    gain.disconnect();
  });
  melodyNodes = [];
  updateMelodyButton();
}
async function playReferenceMelody() {
  if (!reference.length) {
    status.textContent = 'Carregue um vídeo com arquivo de referência para ouvir a melodia.';
    return;
  }
  if (melodyNodes.length) {
    stopMelody();
    return;
  }
  melodyContext ||= new AudioContext();
  await melodyContext.resume();
  const fromTime = video.currentTime || 0;
  const now = melodyContext.currentTime + 0.03;
  for (const referenceNote of reference) {
    const note = noteFromReference(referenceNote);
    if (!note || !Number.isInteger(note.midi) || referenceNote.end <= fromTime) continue;
    const start = Math.max(referenceNote.start, fromTime);
    const duration = referenceNote.end - start;
    if (duration <= 0) continue;
    const startAt = now + start - fromTime;
    const endAt = startAt + duration;
    const oscillator = melodyContext.createOscillator();
    const gain = melodyContext.createGain();
    oscillator.type = 'triangle';
    oscillator.frequency.value = midiToFrequency(note.midi);
    gain.gain.setValueAtTime(0, startAt);
    gain.gain.linearRampToValueAtTime(0.12, startAt + Math.min(0.02, duration / 2));
    gain.gain.setValueAtTime(0.12, Math.max(startAt + 0.02, endAt - 0.02));
    gain.gain.linearRampToValueAtTime(0, endAt);
    oscillator.connect(gain).connect(melodyContext.destination);
    const node = { oscillator, gain };
    oscillator.onended = () => {
      melodyNodes = melodyNodes.filter((item) => item !== node);
      oscillator.disconnect();
      gain.disconnect();
      updateMelodyButton();
    };
    melodyNodes.push(node);
    oscillator.start(startAt);
    oscillator.stop(endAt);
  }
  if (melodyNodes.length) {
    status.textContent = 'Melodia de referência em reprodução.';
    updateMelodyButton();
  }
}

function noteFromReference(referenceNote) {
  if (Number.isInteger(referenceNote.midi)) {
    const midi = referenceNote.midi;
    const pitchClassIndex = ((midi % 12) + 12) % 12;
    return { midi, pitchClassIndex, pitchClass: PITCH_CLASSES[pitchClassIndex], name: referenceNote.note_name || `${PITCH_CLASSES[pitchClassIndex]}${Math.floor(midi / 12) - 1}` };
  }
  const match = typeof referenceNote.note_name === 'string' && referenceNote.note_name.match(/^([A-G](?:#)?)/);
  const pitchClassIndex = match ? PITCH_CLASSES.indexOf(match[1]) : -1;
  return pitchClassIndex >= 0 ? { pitchClassIndex, pitchClass: match[1], name: referenceNote.note_name } : null;
}

function detectPitch(buffer, sampleRate) {
  let bestLag = 0;
  let best = 0;
  for (let lag = Math.floor(sampleRate / 1000); lag < Math.floor(sampleRate / 75); lag += 1) {
    let correlation = 0;
    for (let index = 0; index < buffer.length - lag; index += 1) correlation += buffer[index] * buffer[index + lag];
    if (correlation > best) { best = correlation; bestLag = lag; }
  }
  return bestLag && best > 0.01 ? sampleRate / bestLag : null;
}

function recordPerformanceFrame(time, level, sungNote) {
  if (time - lastPerformanceFrameTime < analysisFrameIntervalSeconds) return;
  performanceFrames.push({ time, level, midi: sungNote?.midi ?? null });
  lastPerformanceFrameTime = time;
}

function referenceSequence(untilTime = Infinity) {
  const sequence = [];
  for (const [noteIndex, note] of reference.entries()) {
    const resolved = noteFromReference(note);
    if (!resolved || !Number.isFinite(note.start) || !Number.isFinite(note.end) || note.start > untilTime) continue;
    for (let time = note.start; time < Math.min(note.end, untilTime); time += analysisFrameIntervalSeconds) {
      sequence.push({ time, midi: resolved.midi, pitchClassIndex: resolved.pitchClassIndex, noteIndex });
    }
  }
  return compactSequence(sequence);
}

function performanceSequence() {
  return compactSequence(
    performanceFrames
      .filter((frame) => frame.level >= silenceThreshold && Number.isInteger(frame.midi))
      .map((frame) => ({ ...frame, pitchClassIndex: ((frame.midi % 12) + 12) % 12 })),
  );
}

function alignmentScore(untilTime = Infinity) {
  const expected = referenceSequence(untilTime);
  const sung = performanceSequence();
  const expectedNotes = new Set(expected.map((frame) => frame.noteIndex));
  if (!expected.length || !sung.length) return { score: 0, matches: 0, expected: expectedNotes.size, sung: sung.length };

  const columns = sung.length + 1;
  const directions = new Uint8Array((expected.length + 1) * columns);
  const gapCost = 0.75;
  let previous = new Float32Array(columns);
  let current = new Float32Array(columns);
  for (let column = 1; column < columns; column += 1) previous[column] = column * gapCost;

  for (let row = 1; row <= expected.length; row += 1) {
    current[0] = row * gapCost;
    for (let column = 1; column < columns; column += 1) {
      const distance = pitchClassDistance(expected[row - 1].pitchClassIndex, sung[column - 1].pitchClassIndex);
      const diagonal = previous[column - 1] + (distance <= Number(tolerance.value) ? 0 : 1 + distance);
      const up = previous[column] + gapCost;
      const left = current[column - 1] + gapCost;
      if (diagonal <= up && diagonal <= left) {
        current[column] = diagonal;
        directions[row * columns + column] = 0;
      } else if (up <= left) {
        current[column] = up;
        directions[row * columns + column] = 1;
      } else {
        current[column] = left;
        directions[row * columns + column] = 2;
      }
    }
    [previous, current] = [current, previous];
  }

  let row = expected.length;
  let column = sung.length;
  const matchedNotes = new Set();
  while (row > 0 && column > 0) {
    const direction = directions[row * columns + column];
    if (direction === 0) {
      const distance = pitchClassDistance(expected[row - 1].pitchClassIndex, sung[column - 1].pitchClassIndex);
      if (distance <= Number(tolerance.value)) matchedNotes.add(expected[row - 1].noteIndex);
      row -= 1;
      column -= 1;
    } else if (direction === 1) {
      row -= 1;
    } else {
      column -= 1;
    }
  }
  return {
    score: (matchedNotes.size / expectedNotes.size) * 100,
    matches: matchedNotes.size,
    expected: expectedNotes.size,
    sung: sung.length,
  };
}

function updateLiveScore() {
  if (video.currentTime - lastLiveScoreTime < 0.5) return;
  lastLiveScoreTime = video.currentTime;
  const analysis = alignmentScore(video.currentTime);
  scoreBox.textContent = analysis.sung ? `Acerto: ${(analysis.score / 10).toFixed(1)}` : 'Acerto: —';
}

function evaluatePitch() {
  if (!analyser || video.paused) return;
  const { buffer, level } = sampleMicrophone();
  const rawPitch = level >= silenceThreshold ? detectPitch(buffer, microphone.sampleRate) : null;
  const pitch = smoothPitch(rawPitch, pitchHistory);
  const sungNote = noteFromFrequency(pitch);
  recordPerformanceFrame(video.currentTime, level, sungNote);
  updateLiveScore();
  const referenceTime = Math.max(0, video.currentTime - Number(micLatency.value) / 1000);
  const expected = referenceAt(referenceTime);
  if (!expected) { feedback.textContent = 'Trecho sem nota de referência'; return; }
  if (referenceTime < expected.start + NOTE_START_WINDOW_SECONDS) {
    feedback.textContent = 'Aguardando a entrada da nota';
    return;
  }
  if (level < silenceThreshold) {
    feedback.textContent = 'Aguardando sua entrada';
    return;
  }
  const expectedNote = noteFromReference(expected);
  if (!expectedNote || !sungNote) { feedback.textContent = `Esperado: ${expected.note_name}`; return; }
  const hit = pitchClassDistance(sungNote.pitchClassIndex, expectedNote.pitchClassIndex) <= Number(tolerance.value);
  feedback.textContent = `${hit ? '✓ No tom' : '• Ajuste a voz'} · esperado ${expectedNote.name} · você ${sungNote.name}`;
}

function startLoop() {
  evaluatePitch();
  if (!video.paused) requestAnimationFrame(startLoop);
}

async function enableMicrophone() {
  if (microphone) return;
  stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  microphone = new AudioContext();
  await microphone.resume();
  analyser = microphone.createAnalyser();
  microphoneGain = microphone.createGain();
  microphoneGain.gain.value = Number(document.querySelector('#gain').value);
  analyser.fftSize = 2048;
  microphone.createMediaStreamSource(stream).connect(microphoneGain).connect(analyser);
}

async function averageNoiseLevel(durationMilliseconds) {
  const levels = [];
  const deadline = performance.now() + durationMilliseconds;
  while (performance.now() < deadline) {
    levels.push(sampleMicrophone().level);
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }
  return levels.reduce((sum, level) => sum + level, 0) / levels.length;
}

async function measureMicrophoneLatency() {
  const toneFrequency = 440;
  const delayMilliseconds = 500;
  const deadline = performance.now() + delayMilliseconds + 2500;
  const scheduledAt = performance.now() + delayMilliseconds;
  const calibrationHistory = [];
  const oscillator = microphone.createOscillator();
  const gain = microphone.createGain();
  oscillator.frequency.value = toneFrequency;
  gain.gain.value = 0.15;
  oscillator.connect(gain).connect(microphone.destination);
  oscillator.start(microphone.currentTime + delayMilliseconds / 1000);
  oscillator.stop(microphone.currentTime + (delayMilliseconds + 400) / 1000);
  while (performance.now() < deadline) {
    const { buffer, level } = sampleMicrophone();
    const pitch = smoothPitch(detectPitch(buffer, microphone.sampleRate), calibrationHistory);
    const detected = noteFromFrequency(pitch);
    if (performance.now() >= scheduledAt && level >= silenceThreshold && detected && Math.abs(detected.midi - 69) <= 1) {
      return Math.round(performance.now() - scheduledAt);
    }
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }
  return null;
}

async function runCalibration() {
  closeCalibration.hidden = true;
  calibrationTitle.textContent = 'Preparando o microfone';
  calibrationText.textContent = 'Permita o acesso ao microfone e fique em silêncio por dois segundos.';
  calibration.showModal();
  try {
    await enableMicrophone();
    const noiseLevel = await averageNoiseLevel(2000);
    silenceThreshold = Math.max(0.008, noiseLevel * 3);
    calibrationTitle.textContent = 'Medindo a latência';
    calibrationText.textContent = 'Um tom de teste será reproduzido. Use os alto-falantes por alguns segundos para o microfone conseguir ouvi-lo.';
    await wait(800);
    const latency = await measureMicrophoneLatency();
    if (latency === null) {
      calibrationTitle.textContent = 'Ruído ambiente calibrado';
      calibrationText.textContent = 'Não foi possível detectar o tom de teste. Mantenha 100 ms ou ajuste a compensação manualmente.';
    } else {
      const boundedLatency = Math.max(0, Math.min(500, Math.round(latency / 10) * 10));
      micLatency.value = String(boundedLatency);
      micLatencyValue.textContent = `${boundedLatency} ms`;
      calibrationTitle.textContent = 'Calibração concluída';
      calibrationText.textContent = `Ruído ambiente ajustado e compensação definida para ${boundedLatency} ms.`;
    }
  } catch {
    calibrationTitle.textContent = 'Não foi possível calibrar';
    calibrationText.textContent = 'Verifique a permissão do microfone e tente novamente.';
  }
  closeCalibration.hidden = false;
}

function resetSession() {
  performanceFrames = [];
  lastPerformanceFrameTime = -Infinity;
  lastLiveScoreTime = -Infinity;
  pitchHistory = [];
  scoreBox.textContent = 'Resultado ao término';
}

function showResult(analysis = alignmentScore()) {
  const score = analysis.score;
  const performanceFrames = analysis.performance_frames ?? analysis.sung ?? 0;
  const icon = document.querySelector('#result-icon');
  const title = document.querySelector('#result-title');
  const message = document.querySelector('#result-text');
  if (score >= 100) {
    result.dataset.tier = 'celebration';
    icon.textContent = '🏆';
    title.textContent = 'Perfeito!';
    message.textContent = 'Você dominou cada nota da música.';
  } else if (score >= 75) {
    result.dataset.tier = 'celebration';
    icon.textContent = '🎉';
    title.textContent = 'Excelente!';
    message.textContent = 'Você está muito no tom.';
  } else if (score >= 50) {
    result.dataset.tier = 'improve';
    icon.textContent = '🌱';
    title.textContent = 'Boa evolução';
    message.textContent = 'Continue lapidando as notas.';
  } else if (score >= 30) {
    result.dataset.tier = 'improve';
    icon.textContent = '🎵';
    title.textContent = 'Você está no caminho';
    message.textContent = 'Ouça a melodia e tente novamente.';
  } else if (score >= 10) {
    result.dataset.tier = 'low';
    icon.textContent = '💪';
    title.textContent = 'Bom começo';
    message.textContent = 'A prática vai trazer segurança.';
  } else {
    result.dataset.tier = 'low';
    icon.textContent = '💪';
    title.textContent = 'Vamos tentar de novo';
    message.textContent = performanceFrames ? 'Ainda não chegou a 10% de acerto. Use a melodia de referência e tente novamente.' : 'Nenhuma voz foi detectada durante a música.';
  }
  document.querySelector('#result-score').textContent = (score / 10).toFixed(1);
  scoreBox.textContent = `Resultado: ${(score / 10).toFixed(1)}`;
  result.showModal();
}

function finishSession() {
  showResult();
  performanceFrames = [];
  lastPerformanceFrameTime = -Infinity;
  lastLiveScoreTime = -Infinity;
  pitchHistory = [];
}

async function selectVideo(entry, button) {
  try {
    status.textContent = 'Carregando referência musical…';
    const response = await fetch(`/api/videos/${encodeURIComponent(entry.name)}/audit`);
    if (!response.ok) throw new Error('Arquivo de referência não encontrado');
    const audit = await response.json();
    reference = audit.notes || [];
    const lyricsResponse = await fetch(`/api/videos/${encodeURIComponent(entry.name)}/lyrics`);
    lyrics = lyricsResponse.ok ? (await lyricsResponse.json()).lyrics || [] : audit.lyrics || [];
    stopMelody();
    video.pause();
    video.src = entry.url;
    video.load();
    updateLyrics();
    resetSession();
    document.querySelectorAll('.video-option').forEach((item) => item.classList.remove('active'));
    button.classList.add('active');
    status.textContent = `${entry.name} carregado. Clique em Play para começar.`;
    feedback.textContent = 'Pronto para cantar';
  } catch (error) { status.textContent = error.message; }
}

async function loadVideos() {
  try {
    const response = await fetch('/api/videos');
    if (!response.ok) throw new Error('Não foi possível carregar a biblioteca de vídeos.');
    const entries = await response.json();
    videos.innerHTML = '';
    if (!entries.length) { videos.textContent = 'Nenhum vídeo encontrado.'; return; }
    const available = [];
    entries.forEach((entry) => {
      const button = document.createElement('button');
      button.className = 'video-option';
      button.type = 'button';
      button.disabled = !entry.has_audit;
      button.innerHTML = `${entry.name}<small>${entry.has_audit ? 'Referência pronta' : 'Sem .audit.json'}</small>`;
      button.addEventListener('click', () => selectVideo(entry, button));
      videos.appendChild(button);
      if (entry.has_audit) available.push({ entry, button });
    });
    if (available.length) await selectVideo(available[0].entry, available[0].button);
    else status.textContent = 'Há vídeos na biblioteca, mas nenhum possui o arquivo .audit.json pareado.';
  } catch (error) {
    videos.textContent = 'Não foi possível carregar os vídeos.';
    status.textContent = error.message;
  }
}

document.querySelector('#refresh').addEventListener('click', loadVideos);
document.querySelector('#back').addEventListener('click', () => { video.currentTime = Math.max(0, video.currentTime - 5); });
document.querySelector('#forward').addEventListener('click', () => { video.currentTime = Math.min(video.duration || Infinity, video.currentTime + 5); });
playMelody.addEventListener('click', playReferenceMelody);
document.querySelector('#volume').addEventListener('input', (event) => { video.volume = Number(event.target.value); });
document.querySelector('#gain').addEventListener('input', (event) => { if (microphoneGain) microphoneGain.gain.value = Number(event.target.value); });
micLatency.addEventListener('input', () => { micLatencyValue.textContent = `${micLatency.value} ms`; });
tolerance.addEventListener('input', () => { toleranceValue.textContent = toleranceLabel(Number(tolerance.value)); });
analysisInterval.addEventListener('input', () => {
  analysisFrameIntervalSeconds = Number(analysisInterval.value) / 1000;
  analysisIntervalValue.textContent = `${analysisInterval.value} ms`;
});
calibrateMicrophone.addEventListener('click', runCalibration);
closeCalibration.addEventListener('click', () => calibration.close());
document.querySelector('#close-result').addEventListener('click', () => result.close());
reset.addEventListener('click', () => {
  video.pause();
  video.currentTime = 0;
  stopMelody();
  resetSession();
  updateLyrics();
  play.innerHTML = '▶ <span>Play</span>';
  feedback.textContent = 'Tentativa reiniciada';
  status.textContent = 'Vídeo reiniciado. Clique em Play para começar uma nova tentativa.';
  if (result.open) result.close();
});

play.addEventListener('click', async () => {
  if (!video.src) { status.textContent = 'Selecione um vídeo com referência primeiro.'; return; }
  if (!video.paused) {
    video.pause();
    play.innerHTML = '▶ <span>Play</span>';
    return;
  }
  try {
    await video.play();
    play.innerHTML = '❚❚ <span>Pausar</span>';
    try {
      await enableMicrophone();
      startLoop();
    } catch {
      status.textContent = 'Vídeo em reprodução. Não foi possível acessar o microfone; verifique a permissão para avaliar a afinação.';
    }
  } catch { status.textContent = 'Não foi possível iniciar o vídeo.'; }
});

video.addEventListener('error', () => {
  play.innerHTML = '▶ <span>Play</span>';
  feedback.textContent = 'Não foi possível carregar o vídeo';
  status.textContent = 'O navegador não conseguiu carregar este vídeo. Verifique se o arquivo é um MP4 compatível.';
});
video.addEventListener('timeupdate', updateLyrics);
video.addEventListener('ended', () => { stopMelody(); updateLyrics(); play.innerHTML = '▶ <span>Play</span>'; finishSession(); });
loadVideos();
