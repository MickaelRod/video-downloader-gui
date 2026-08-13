"""Unit tests for the pure, Tkinter-free helper functions in video_downloader_gui.py."""

import os

import pytest

from video_downloader_gui import (
    codec_short_label,
    ensure_mp4_extension,
    format_file_size,
    get_downloads_folder,
    is_bot_check_error,
    is_curl_cffi_related_error,
    parse_ffmpeg_progress_line,
    parse_ytdlp_progress_line,
    remove_leftover_part_files,
    sanitize_filename,
)


# ---------- sanitize_filename ----------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Normal Title", "Normal Title"),
        ("Title | Subtitle", "Title - Subtitle"),
        ('Bad:/\\*?"<>Chars', "Bad________Chars"),
        ("  spaced  ", "spaced"),
        ("", "Video"),
        ("   ", "Video"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


# ---------- ensure_mp4_extension ----------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("myvideo", "myvideo.mp4"),
        ("myvideo.mp4", "myvideo.mp4"),
        ("myvideo.MOV", "myvideo.mp4"),
        ("myvideo.mkv", "myvideo.mp4"),
        ("", "Video.mp4"),
        ("   ", "Video.mp4"),
        ("  myvideo  ", "myvideo.mp4"),
    ],
)
def test_ensure_mp4_extension(raw, expected):
    assert ensure_mp4_extension(raw) == expected


# ---------- format_file_size ----------

@pytest.mark.parametrize(
    "num_bytes, expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024 * 1024, "1.0 MB"),
        (1024 * 1024 * 1024, "1.0 GB"),
        (1024 * 1024 * 1024 * 5, "5.0 GB"),
    ],
)
def test_format_file_size(num_bytes, expected):
    assert format_file_size(num_bytes) == expected


# ---------- codec_short_label ----------

@pytest.mark.parametrize(
    "codec, expected",
    [
        ("avc1.640028", "AVC"),
        ("av01.0.05M.08", "AV1"),
        ("vp9", "VP9"),
        ("vp09.00.10.08", "VP9"),
        ("hev1.1.6.L93.B0", "HEVC"),
        ("hvc1.2.4.L120.B0", "HEVC"),
        ("mp4a.40.2", "MP4A"),
        ("unknown_codec", "UNKNOWN_CODEC"),
    ],
)
def test_codec_short_label(codec, expected):
    assert codec_short_label(codec) == expected


# ---------- is_curl_cffi_related_error ----------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("ERROR: curl_cffi is required", True),
        ("failed to impersonate browser", True),
        ("CURL_CFFI missing", True),
        ("some unrelated network error", False),
        ("", False),
    ],
)
def test_is_curl_cffi_related_error(text, expected):
    assert is_curl_cffi_related_error(text) == expected


# ---------- is_bot_check_error ----------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("Sign in to confirm you're not a bot", True),
        ("sign in to confirm your age", True),  # substring match is intentionally broad
        ("Please confirm you're not a bot before continuing", True),
        ("some unrelated network error", False),
        ("", False),
    ],
)
def test_is_bot_check_error(text, expected):
    assert is_bot_check_error(text) == expected


# ---------- parse_ytdlp_progress_line ----------

@pytest.mark.parametrize(
    "line, expected",
    [
        ("[download]  42.3% of  161.66MiB at  102.79MiB/s ETA 00:05", 42.3),
        ("[download] 100.0% of  161.66MiB in 00:00:02", 100.0),
        ("[download]   0.0% of  161.66MiB", 0.0),
        ("some unrelated output line", None),
        ("", None),
    ],
)
def test_parse_ytdlp_progress_line(line, expected):
    assert parse_ytdlp_progress_line(line) == expected


# ---------- parse_ffmpeg_progress_line ----------

def test_parse_ffmpeg_progress_line_none_duration():
    assert parse_ffmpeg_progress_line("out_time_ms=5000000", None) is None


def test_parse_ffmpeg_progress_line_zero_duration():
    assert parse_ffmpeg_progress_line("out_time_ms=5000000", 0) is None


def test_parse_ffmpeg_progress_line_no_match():
    assert parse_ffmpeg_progress_line("frame=100", 60.0) is None


def test_parse_ffmpeg_progress_line_midway():
    # 30s elapsed out of 60s total = 50%
    assert parse_ffmpeg_progress_line("out_time_ms=30000000", 60.0) == pytest.approx(50.0)


def test_parse_ffmpeg_progress_line_clamped_to_100():
    # elapsed exceeds total duration (can happen near the end) -> clamped
    assert parse_ffmpeg_progress_line("out_time_ms=90000000", 60.0) == 100.0


# ---------- get_downloads_folder ----------

def test_get_downloads_folder_is_under_home():
    folder = get_downloads_folder()
    assert folder == os.path.join(os.path.expanduser("~"), "Downloads")


# ---------- remove_leftover_part_files ----------

def test_remove_leftover_part_files(tmp_path):
    destination = tmp_path / "MyVideo.mp4"
    (tmp_path / "MyVideo.mp4.part").write_text("partial")
    (tmp_path / "MyVideo.mp4.part-Frag3").write_text("partial")
    (tmp_path / "MyVideo.mp4.ytdl").write_text("meta")
    (tmp_path / "MyVideo.mp4").write_text("unrelated, should not be removed by this call")
    (tmp_path / "OtherVideo.mp4.part").write_text("unrelated video, must survive")

    remove_leftover_part_files(str(destination))

    remaining = {entry.name for entry in tmp_path.iterdir()}
    assert remaining == {"MyVideo.mp4", "OtherVideo.mp4.part"}


def test_remove_leftover_part_files_no_leftovers(tmp_path):
    destination = tmp_path / "MyVideo.mp4"
    (tmp_path / "MyVideo.mp4").write_text("final file only")

    remove_leftover_part_files(str(destination))

    remaining = {entry.name for entry in tmp_path.iterdir()}
    assert remaining == {"MyVideo.mp4"}
