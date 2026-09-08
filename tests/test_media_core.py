import unittest

from acan_studio.core.media import (
    build_mp3_to_wav_command,
    calculate_target_bitrates,
    classify_content_type,
    detect_platform,
    extract_first_url,
    format_srt_time,
    segments_from_srt,
    segments_to_srt,
    srt_to_plain_text,
)


class MediaCoreTests(unittest.TestCase):
    def test_mp3_to_wav_uses_compatible_pcm_without_changing_layout(self):
        command = build_mp3_to_wav_command(
            "/tools/ffmpeg",
            "/input/My Song.mp3",
            "/output/My Song.wav",
        )
        self.assertEqual(command[0], "/tools/ffmpeg")
        self.assertEqual(command[-1], "/output/My Song.wav")
        self.assertEqual(command[command.index("-c:a") + 1], "pcm_s16le")
        self.assertEqual(command[command.index("-map") + 1], "0:a:0")
        self.assertNotIn("-ar", command)
        self.assertNotIn("-ac", command)

    def test_extract_first_url_removes_share_text_punctuation(self):
        text = "复制打开： https://youtu.be/example?id=1。谢谢"
        self.assertEqual(extract_first_url(text), "https://youtu.be/example?id=1")

    def test_detect_platform_uses_host_boundaries(self):
        youtube = {"name": "YouTube", "hosts": ("youtube.com", "youtu.be")}
        unknown = {"name": "Other"}
        self.assertIs(detect_platform("https://www.youtube.com/watch?v=abc", [youtube], unknown), youtube)
        self.assertIs(detect_platform("https://notyoutube.com/watch?v=abc", [youtube], unknown), unknown)

    def test_classify_content_type(self):
        self.assertEqual(classify_content_type("https://www.douyin.com/video/123", "抖音"), "video")
        self.assertEqual(classify_content_type("https://www.douyin.com/note/123", "抖音"), "note")
        self.assertEqual(classify_content_type("https://www.youtube.com/playlist?list=abc", "YouTube"), "collection")

    def test_target_bitrate_requires_positive_duration(self):
        video_bitrate, audio_bitrate = calculate_target_bitrates(200, 120)
        self.assertGreaterEqual(video_bitrate, 100)
        self.assertEqual(audio_bitrate, 64)
        with self.assertRaises(ValueError):
            calculate_target_bitrates(200, 0)

    def test_srt_round_trip_and_millisecond_carry(self):
        self.assertEqual(format_srt_time(59.9996), "00:01:00,000")
        content = segments_to_srt([
            {"start": 0.0, "end": 1.25, "text": "Hello"},
            {"start": 1.5, "end": 2.0, "text": "World"},
        ])
        segments = segments_from_srt(content)
        self.assertEqual([segment["text"] for segment in segments], ["Hello", "World"])
        self.assertEqual(srt_to_plain_text(content), "Hello\nWorld\n")


if __name__ == "__main__":
    unittest.main()
