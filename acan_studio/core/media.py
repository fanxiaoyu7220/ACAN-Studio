"""Pure media and input helpers used by the desktop application.

This module deliberately has no GUI or third-party imports. Keeping these
operations here makes the download/compression/subtitle behavior easy to test
and gives future interfaces a stable place to call into.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,;:!?)]}>\"'，。；：！？）》】」』"


def extract_first_url(text: str | None) -> str | None:
    """Return the first HTTP(S) URL from pasted text.

    Mobile share text often wraps a URL in Chinese or Markdown punctuation.
    The punctuation is not part of the URL and should not be handed to
    yt-dlp.
    """

    match = URL_PATTERN.search(text or "")
    if not match:
        return None
    raw_url = re.split(r"[，。；：！？）》】」』]", match.group(0), maxsplit=1)[0]
    return raw_url.rstrip(TRAILING_URL_PUNCTUATION)


def detect_platform(url: str | None, platform_specs, unknown_platform):
    """Match a URL against the application's platform registry."""

    host = urlparse(url or "").netloc.lower()
    normalized_host = host[4:] if host.startswith("www.") else host

    for platform in platform_specs:
        for item in platform.get("hosts", ()):
            if normalized_host == item or normalized_host.endswith(f".{item}"):
                return platform
    return unknown_platform


def classify_content_type(url: str | None, platform_name: str) -> str:
    """Classify a link before invoking a download engine."""

    parsed = urlparse(url or "")
    path = parsed.path.lower()
    host = parsed.netloc.lower()
    query = parsed.query.lower()

    if "live" in path or "live" in host:
        return "live"
    if any(token in path for token in ("/collection", "/playlist", "/series", "/channel/collection")):
        return "collection"
    if any(token in path for token in ("/user/", "/profile/", "/channel/", "/space/")) and "/video/" not in path:
        return "profile"

    if platform_name == "抖音":
        if "/video/" in path:
            return "video"
        if "/note/" in path:
            return "note"
        if "/jingxuan" in path:
            return "collection"

    if platform_name == "小红书":
        if "type=video" in query:
            return "video"
        if any(token in path for token in ("/explore/", "/discovery/item/", "/item/")):
            return "video"
        if "note" in path:
            return "note"

    if platform_name in ("YouTube", "B站", "微博", "芒果TV"):
        if path and path != "/":
            return "video"

    return "unknown"


def calculate_target_bitrates(
    target_size_mb: float,
    duration_seconds: float,
    audio_bitrate_kbps: int = 64,
    safety_ratio: float = 0.96,
) -> tuple[int, int]:
    """Calculate two-pass video/audio bitrates for a target file size."""

    target_size_mb = float(target_size_mb)
    duration_seconds = float(duration_seconds)
    audio_bitrate_kbps = int(audio_bitrate_kbps)
    safety_ratio = float(safety_ratio)

    if target_size_mb <= 0:
        raise ValueError("target_size_mb must be greater than zero")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if audio_bitrate_kbps < 0:
        raise ValueError("audio_bitrate_kbps cannot be negative")
    if not 0 < safety_ratio <= 1:
        raise ValueError("safety_ratio must be greater than zero and at most one")

    # 1 MB is approximately 8192 kilobits. Leave a small margin so container
    # overhead does not push the finished file above the requested size.
    target_total_kbits = target_size_mb * 8192 * safety_ratio
    total_bitrate_kbps = target_total_kbits / duration_seconds
    video_bitrate_kbps = int(total_bitrate_kbps - audio_bitrate_kbps)
    return max(video_bitrate_kbps, 100), audio_bitrate_kbps


def build_mp3_to_wav_command(ffmpeg_path, input_path, output_path) -> list[str]:
    """Build a broadly compatible, uncompressed PCM WAV conversion command.

    The source sample rate and channel layout are intentionally preserved while
    the decoded audio is written as signed 16-bit little-endian PCM.
    """

    return [
        str(ffmpeg_path),
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:a:0",
        "-vn",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]


def format_duration(seconds: float) -> str:
    """Format seconds for the Chinese desktop UI."""

    total_seconds = max(0, int(float(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remain = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes}分{remain}秒"
    return f"{minutes}分{remain}秒"


def format_file_size(size_bytes: int | float) -> str:
    """Format a byte count with a compact binary unit."""

    size = max(0.0, float(size_bytes))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{size:.1f}GB"


def parse_srt_time(value: str) -> float:
    """Parse ``HH:MM:SS,mmm`` or ``HH:MM:SS.mmm`` into seconds."""

    normalized = (value or "").strip().replace(",", ".")
    try:
        parts = normalized.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (TypeError, ValueError):
        pass
    return 0.0


def segments_from_srt(content: str) -> list[dict[str, float | str]]:
    """Read simple SRT blocks into timestamped transcript segments."""

    segments = []
    blocks = re.split(r"\n\s*\n", (content or "").strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        time_line = next((line for line in lines if "-->" in line), "")
        if not time_line:
            continue
        start_text, end_text = [part.strip() for part in time_line.split("-->", 1)]
        text_lines = [line for line in lines if line != time_line and not line.isdigit()]
        text = " ".join(text_lines).strip()
        if not text:
            continue
        segments.append({
            "start": parse_srt_time(start_text),
            "end": parse_srt_time(end_text),
            "text": text,
        })
    return segments


def srt_to_plain_text(content: str) -> str:
    """Remove SRT metadata and duplicate caption lines."""

    lines = []
    seen = set()
    for line in (content or "").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.isdigit() or "-->" in cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(cleaned)
    return "\n".join(lines) + ("\n" if lines else "")


def format_srt_time(seconds: float) -> str:
    """Format seconds as an SRT timestamp with correct millisecond carry."""

    total_milliseconds = max(0, int(round(float(seconds or 0) * 1000)))
    total_seconds, milliseconds = divmod(total_milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def segments_to_srt(segments) -> str:
    """Serialize transcript segments to SRT."""

    blocks = []
    for segment in segments or []:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        blocks.append(
            f"{len(blocks) + 1}\n"
            f"{format_srt_time(segment.get('start', 0))} --> {format_srt_time(segment.get('end', 0))}\n"
            f"{text}\n"
        )
    if not blocks:
        return "1\n00:00:00,000 --> 00:00:01,000\n未识别到清晰语音内容。\n"
    return "\n".join(blocks) + "\n"
