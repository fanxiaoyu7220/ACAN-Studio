import unittest
from pathlib import Path

from acan_studio.core.downloader import build_yt_dlp_download_attempts
from acan_studio.core.errors import platform_stage_suggestion


class YouTubeResilienceTests(unittest.TestCase):
    def setUp(self):
        self.platform = {"name": "YouTube"}
        self.engine = {"name": "Engine A：yt-dlp"}

    def test_download_attempts_switch_transport_and_keep_resume(self):
        attempts = build_yt_dlp_download_attempts(
            self.platform,
            "https://youtu.be/HZguePfneD8",
            Path("/tmp/ACAN Test"),
            self.engine,
            cookie_args=["--cookies-from-browser", "chrome"],
            deno_path="/bundle/deno",
            curl_path="/usr/bin/curl",
            proxy_url="http://127.0.0.1:7890",
        )

        self.assertEqual(len(attempts), 3)
        first_command = attempts[0][1]
        second_command = attempts[1][1]
        curl_command = attempts[2][1]

        self.assertIn("2M", first_command)
        self.assertIn("512K", second_command)
        self.assertIn("--continue", first_command)
        self.assertIn("--continue", second_command)
        self.assertNotIn("infinite", first_command)
        self.assertNotIn("infinite", second_command)
        self.assertIn("http:/usr/bin/curl", curl_command)
        self.assertEqual(curl_command[curl_command.index("--proxy") + 1], "http://127.0.0.1:7890")
        self.assertIn("--retry-all-errors", curl_command[curl_command.index("--downloader-args") + 1])

    def test_douyin_does_not_read_cookies_by_default(self):
        attempts = build_yt_dlp_download_attempts(
            {"name": "抖音"},
            "https://www.douyin.com/video/123",
            Path("/tmp/ACAN Test"),
            self.engine,
        )

        self.assertEqual(len(attempts), 1)
        self.assertNotIn("--cookies-from-browser", attempts[0][1])

    def test_weibo_cookie_retry_is_opt_in(self):
        attempts = build_yt_dlp_download_attempts(
            {"name": "微博"},
            "https://weibo.com/tv/show/123?fid=abc",
            Path("/tmp/ACAN Test"),
            self.engine,
            cookie_args=["--cookies-from-browser", "chrome"],
        )

        self.assertEqual(len(attempts), 4)
        self.assertNotIn("--cookies-from-browser", attempts[0][1])
        self.assertIn("--cookies-from-browser", attempts[2][1])

    def test_ssl_error_has_specific_chinese_suggestion(self):
        suggestion = platform_stage_suggestion(
            "YouTube",
            "下载",
            "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol",
        )

        self.assertIn("分块断点续传", suggestion)
        self.assertIn(".part", suggestion)

    def test_mgtv_geo_restriction_has_specific_chinese_suggestion(self):
        suggestion = platform_stage_suggestion(
            "芒果TV",
            "下载",
            "This video is not available from your location due to geo restriction",
        )

        self.assertIn("地区或版权限制", suggestion)
        self.assertIn("浏览器", suggestion)


if __name__ == "__main__":
    unittest.main()
