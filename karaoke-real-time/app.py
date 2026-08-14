from __future__ import annotations

import argparse
import queue
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pitch import detect_pitch
from reference import audit_path_for, find_videos, load_reference, note_at
from scoring import PitchScore


class KaraokeWindow(QMainWindow):
    """Janela de reprodução com feedback de afinação no canto superior direito."""

    def __init__(
        self,
        library: Path,
        initial_video: Path | None,
        override_reference: Path | None,
        device: int | str | None,
        tolerance_cents: float,
    ) -> None:
        super().__init__()
        if not library.is_dir():
            raise NotADirectoryError(f"Biblioteca de vídeos inexistente: {library}")
        self.library = library
        self.initial_video = initial_video.resolve() if initial_video else None
        self.override_reference = override_reference
        self.notes = []

        self.tolerance_cents = tolerance_cents
        self.sample_rate = 44_100
        self.microphone_gain = 1.0
        self.microphone: queue.Queue[np.ndarray] = queue.Queue(maxsize=4)
        self.score = PitchScore()
        self.final_shown = False
        self.last_position = 0

        self.setWindowTitle("Karaoke Real Time")
        self.resize(1100, 760)
        self.video_widget = QVideoWidget()
        self.score_label = QLabel("Acerto: 0.0%", self.video_widget)
        self.score_label.setStyleSheet(
            "background: rgba(0, 0, 0, 180); color: #ffff00; border: 2px solid black; "
            "border-radius: 6px; font-size: 22px; font-weight: bold; padding: 8px;"
        )
        self.score_label.raise_()

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)
        self.player.setVideoOutput(self.video_widget)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.positionChanged.connect(self._position_changed)

        controls = QHBoxLayout()
        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self._toggle_playback)
        back_button = QPushButton("⏪ Voltar 5 s")
        back_button.clicked.connect(lambda: self._seek(-5_000))
        forward_button = QPushButton("Avançar 5 s ⏩")
        forward_button.clicked.connect(lambda: self._seek(5_000))
        controls.addWidget(back_button)
        controls.addWidget(self.play_button)
        controls.addWidget(forward_button)
        controls.addSpacing(16)
        controls.addWidget(QLabel("Volume"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(lambda value: self.audio_output.setVolume(value / 100))
        controls.addWidget(self.volume_slider)
        controls.addWidget(QLabel("Ganho microfone"))
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(0, 200)
        self.gain_slider.setValue(100)
        self.gain_slider.valueChanged.connect(lambda value: setattr(self, "microphone_gain", value / 100))
        controls.addWidget(self.gain_slider)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(self.video_widget, stretch=1)
        content_layout.addLayout(controls)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.addWidget(QLabel("Vídeos"))
        self.video_list = QListWidget()
        self.video_list.itemSelectionChanged.connect(self._load_selected_video)
        sidebar_layout.addWidget(self.video_list, stretch=1)
        refresh_button = QPushButton("⟳ Atualizar lista")
        refresh_button.clicked.connect(self._populate_sidebar)
        sidebar_layout.addWidget(refresh_button)
        self.library_status = QLabel()
        self.library_status.setWordWrap(True)
        sidebar_layout.addWidget(self.library_status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(sidebar)
        splitter.addWidget(content)
        splitter.setSizes([260, 840])
        self.setCentralWidget(splitter)

        self.analysis_timer = QTimer(self)
        self.analysis_timer.setInterval(75)
        self.analysis_timer.timeout.connect(self._process_microphone)
        self.analysis_timer.start()
        self.stream = sd.InputStream(
            device=device,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=4_096,
            callback=self._receive_microphone,
        )
        self.stream.start()
        self._populate_sidebar()
        print("Use fones de ouvido para evitar que o áudio do vídeo entre no microfone.")

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        size = self.score_label.sizeHint()
        self.score_label.move(max(8, self.video_widget.width() - size.width() - 16), 16)

    def _receive_microphone(self, indata: np.ndarray, frame_count: int, time_info: object, status: sd.CallbackFlags) -> None:
        if status:
            print(f"[áudio] {status}")
        try:
            self.microphone.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass

    def _toggle_playback(self) -> None:
        if not self.notes:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_button.setText("▶ Play")
        else:
            self.player.play()
            self.play_button.setText("⏸ Pause")

    def _seek(self, offset_ms: int) -> None:
        target = max(0, min(self.player.duration(), self.player.position() + offset_ms))
        if target < self.player.position():
            self._reset_score()
        self.player.setPosition(target)

    def _position_changed(self, position: int) -> None:
        if position < self.last_position - 1_000:
            self._reset_score()
        self.last_position = position

    def _process_microphone(self) -> None:
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return
        try:
            samples = self.microphone.get_nowait() * self.microphone_gain
        except queue.Empty:
            return
        elapsed = self.player.position() / 1_000
        expected = note_at(self.notes, elapsed)
        detected = detect_pitch(np.clip(samples, -1, 1), self.sample_rate)
        deviation = self.score.evaluate(detected, expected, self.tolerance_cents)
        self.score_label.setText(f"Acerto: {self.score.rate:.1f}%")
        if expected and detected and deviation is not None:
            print(f"t={elapsed:6.1f}s | esperado={expected.note_name} | {deviation:+.0f} cents | acerto={self.score.rate:.1f}%")

    def _populate_sidebar(self) -> None:
        videos = find_videos(self.library)
        self.video_list.blockSignals(True)
        self.video_list.clear()
        for video in videos:
            item = QListWidgetItem(video.name)
            item.setData(Qt.ItemDataRole.UserRole, str(video))
            if not audit_path_for(video).is_file():
                item.setText(f"⚠ {video.name}")
            self.video_list.addItem(item)
        self.video_list.blockSignals(False)
        if not videos:
            self.library_status.setText("Nenhum vídeo encontrado.")
            return
        target = next((index for index, video in enumerate(videos) if self.initial_video and video.resolve() == self.initial_video), 0)
        self.video_list.setCurrentRow(target)

    def _load_selected_video(self) -> None:
        item = self.video_list.currentItem()
        if not item:
            return
        video = Path(item.data(Qt.ItemDataRole.UserRole))
        audit = self.override_reference if self.initial_video and video.resolve() == self.initial_video and self.override_reference else audit_path_for(video)
        self.player.stop()
        self._reset_score()
        self.final_shown = False
        if not audit.is_file():
            self.notes = []
            self.play_button.setEnabled(False)
            self.library_status.setText(f"Sem auditoria: {audit.name}")
            self.score_label.setText("Sem audit.json")
            return
        self.notes = load_reference(audit)
        self.player.setSource(QUrl.fromLocalFile(str(video.resolve())))
        self.play_button.setEnabled(bool(self.notes))
        self.library_status.setText(f"Auditoria: {audit.name}")
        self.setWindowTitle(f"Karaoke Real Time — {video.name}")

    def _reset_score(self) -> None:
        self.score = PitchScore()
        self.score_label.setText("Acerto: 0.0%")

    def _media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia and not self.final_shown:
            self.final_shown = True
            message = f"Sua nota foi: {self.score.rate:.1f}%"
            self.score_label.setText(message)
            print(message)
            QMessageBox.information(self, "Resultado", message)

    def closeEvent(self, event: object) -> None:
        self.analysis_timer.stop()
        self.stream.stop()
        self.stream.close()
        self.player.stop()
        super().closeEvent(event)


def run(library: Path, video: Path | None, reference: Path | None, device: int | str | None, tolerance_cents: float) -> None:
    app = QApplication.instance() or QApplication([])
    window = KaraokeWindow(library, video, reference, device, tolerance_cents)
    window.show()
    app.exec()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara o pitch do microfone com uma música de referência.")
    parser.add_argument("video", type=Path, nargs="?", help="Vídeo inicial (opcional)")
    parser.add_argument("--library", type=Path, default=Path("."), help="Pasta de vídeos (padrão: atual)")
    parser.add_argument("--reference", type=Path, default=None, help="audit.json do vídeo inicial (opcional)")
    parser.add_argument("--device", default=None, help="Índice ou nome do dispositivo de entrada")
    parser.add_argument("--tolerance-cents", type=float, default=50.0, help="Tolerância de afinação (padrão: 50)")
    args = parser.parse_args()
    library = args.video.parent if args.video else args.library
    run(library, args.video, args.reference, args.device, args.tolerance_cents)


if __name__ == "__main__":
    main()
