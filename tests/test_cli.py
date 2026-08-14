from karaoke.cli import cleanup_work_dir


def test_cleanup_removes_only_work_directory(tmp_path):
    work_dir = tmp_path / ".karaoke-work"
    work_dir.mkdir()
    (work_dir / "audio.wav").write_text("intermediário")
    output = tmp_path / "resultado.mp4"
    output.write_text("resultado")

    cleanup_work_dir(work_dir, [output])

    assert not work_dir.exists()
    assert output.exists()


def test_cleanup_rejects_output_inside_work_directory(tmp_path):
    work_dir = tmp_path / ".karaoke-work"
    work_dir.mkdir()
    output = work_dir / "resultado.mp4"

    try:
        cleanup_work_dir(work_dir, [output])
    except ValueError as error:
        assert "dentro do diretório" in str(error)
    else:
        raise AssertionError("A limpeza deveria rejeitar um resultado dentro do diretório de trabalho")
