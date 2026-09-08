"""Dependency-light core helpers for ACAN Studio."""

from .downloader import build_yt_dlp_download_attempts
from .errors import platform_stage_suggestion
from .media import (
    build_mp3_to_wav_command,
    calculate_target_bitrates,
    classify_content_type,
    detect_platform,
    extract_first_url,
    format_duration,
    format_file_size,
    format_srt_time,
    parse_srt_time,
    segments_from_srt,
    segments_to_srt,
    srt_to_plain_text,
)

__all__ = [
    "build_mp3_to_wav_command",
    "build_yt_dlp_download_attempts",
    "calculate_target_bitrates",
    "classify_content_type",
    "detect_platform",
    "extract_first_url",
    "format_duration",
    "format_file_size",
    "format_srt_time",
    "parse_srt_time",
    "platform_stage_suggestion",
    "segments_from_srt",
    "segments_to_srt",
    "srt_to_plain_text",
]
