import os
import queue
import re
import shlex
import shutil
import subprocess
import threading
import tempfile
import webbrowser
import json
import sys
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, getproxies

import customtkinter as ctk
from PIL import Image, ImageTk

from ui_v2 import build_ui_v2
from acan_studio import __version__
from acan_studio.core.network import create_https_context, create_https_opener
from acan_studio.core.downloader import (
    build_yt_dlp_download_attempts,
    build_youtube_network_args,
    clean_url_parameters,
)
from acan_studio.core.errors import platform_stage_suggestion
from acan_studio.core.media import (
    build_mp3_to_wav_command,
    calculate_target_bitrates,
    classify_content_type,
    detect_platform,
    extract_first_url,
    format_duration,
    format_file_size,
    format_srt_time,
    segments_from_srt,
    segments_to_srt,
    srt_to_plain_text,
)


APP_NAME = "ACAN Studio"
SETTINGS_VERSION = 2
CREATOR_DIR = Path.home() / "Movies" / "Creator"
SETTINGS_PATH = Path.home() / "Library" / "Application Support" / "ACAN Studio" / "settings.json"
BILIBILI_DIR = CREATOR_DIR / "Bilibili"
XIAOHONGSHU_DIR = CREATOR_DIR / "Xiaohongshu"
WEIBO_DIR = CREATOR_DIR / "Weibo"
YOUTUBE_DIR = CREATOR_DIR / "YouTube"
DOUYIN_DIR = CREATOR_DIR / "Douyin"
MANGOTV_DIR = CREATOR_DIR / "MangoTV"
OTHER_VIDEO_DIR = CREATOR_DIR / "Other"
AUDIO_DIR = CREATOR_DIR / "Audio"
VIDEO_DIR_NAME = "Video"
NOTE_DIR_NAME = "Note"
FIXED_DIR_NAME = "Fixed"
SUBTITLE_DIR_NAME = "Subtitles"
OCR_DIR_NAME = "OCR_Text"
TRANSCRIPT_DIR_NAME = "Transcript"
COMPRESSED_DIR_NAME = "Compressed"
ENHANCED_DIR_NAME = "Enhanced"
OCR_OUTPUT_NAME = "video_ocr_text.txt"
CONTENT_TYPE_MESSAGES = {
    "video": "视频",
    "note": "图文/笔记",
    "live": "直播",
    "collection": "合集",
    "profile": "用户主页",
    "unknown": "未知",
}
COMMON_TOOL_DIRS = [
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/opt/local/bin",
]
EMBEDDED_TOOL_DIR_NAME = "tools"
EMBEDDED_TESSDATA_DIR_NAME = "tessdata"
EMBEDDED_MODEL_DIR_NAME = "models"
FASTER_WHISPER_MODEL_DIR_NAME = "faster-whisper-base"
YTDLP_PERCENT_PATTERN = re.compile(r"\[download\]\s+(?P<percent>\d+(?:\.\d+)?)%")
YTDLP_SPEED_PATTERN = re.compile(r"\bat\s+(?P<speed>\S+/s)")
YTDLP_ETA_PATTERN = re.compile(r"\bETA\s+(?P<eta>\S+)")
YTDLP_EXPECTED_DURATION_PATTERN = re.compile(r"ACAN_EXPECTED_DURATION=(?P<duration>\d+(?:\.\d+)?)")
YTDLP_DOWNLOADED_FILE_PATTERN = re.compile(r"ACAN_DOWNLOADED_FILE=(?P<path>.+)")
MGTV_SVIP_FILTERS = (
    "mgtv_purview = 200",
    "!mgtv_access_hint",
    "mgtv_access_hint !*= SVIP",
)
DOUYIN_LOGIN_ERROR_KEYWORDS = (
    "login required",
    "authentication",
    "cookie",
)
DOUYIN_COOKIE_PARSE_ERROR_KEYWORDS = (
    "fresh cookies",
    "failed to download web detail json",
    "failed to parse json",
)
DOUYIN_UNSUPPORTED_ERROR_KEYWORDS = ("unsupported url",)
DOUYIN_NETWORK_ERROR_KEYWORDS = (
    "http error",
    "timeout",
    "connection",
)
DOUYIN_WEB_URL = "https://www.douyin.com"
DOUYIN_COOKIE_PARSE_ERROR_MESSAGE = "抖音解析失败，请按下面步骤处理：\n\n1. 运行 yt-dlp -U 更新下载器\n2. 在 Chrome 登录抖音网页版\n3. 播放任意视频 10 秒\n4. 回到 ACAN Studio 重新尝试下载"
DOUYIN_YTDLP_COMPAT_ERROR_MESSAGE = "抖音下载器暂时无法解析，可能是抖音接口或 Cookie 校验问题。"
DOUYIN_LOGIN_ERROR_MESSAGE = "该视频可能需要登录状态。请在 Chrome 登录 douyin.com 后重试。"
DOUYIN_UNSUPPORTED_ERROR_MESSAGE = "当前链接类型暂不支持，请进入视频详情页后重新复制分享链接。"
DOUYIN_NETWORK_ERROR_MESSAGE = "网络异常或平台限制，请稍后重试。"
DOUYIN_JINGXUAN_ERROR_MESSAGE = "检测到这是抖音精选页链接。\n\n目前 yt-dlp 不支持直接下载精选页。\n\n请点击进入具体视频页面后，\n\n使用：\n\n分享 → 复制链接\n\n再粘贴到 ACAN Studio 下载。"
DOUYIN_NOTE_MESSAGE = "这是抖音图文/笔记内容，不是普通视频，请使用图文提取模式。"
WEIBO_VISITOR_ERROR_KEYWORDS = (
    "passport.weibo.com/visitor",
    "visitor/visitor",
    "login",
)
WEIBO_VISITOR_URL_KEYWORDS = (
    "passport.weibo.com",
    "passport.weibo.com/visitor",
    "/visitor/visitor",
)
WEIBO_VISITOR_ERROR_MESSAGE = "微博把下载请求跳转到了登录/访客验证页。请在 Chrome 打开微博网页版，确认已登录，刷新该视频页面并能正常播放后再重试。"
DOWNLOAD_PLATFORMS = {
    "bilibili": {
        "name": "B站",
        "folder": BILIBILI_DIR,
        "folder_name": "Bilibili",
        "hosts": ("bilibili.com", "b23.tv"),
    },
    "xiaohongshu": {
        "name": "小红书",
        "folder": XIAOHONGSHU_DIR,
        "folder_name": "Xiaohongshu",
        "hosts": ("xiaohongshu.com", "xhslink.com", "xhs.com"),
    },
    "weibo": {
        "name": "微博",
        "folder": WEIBO_DIR,
        "folder_name": "Weibo",
        "hosts": ("weibo.com", "weibo.cn", "m.weibo.cn"),
    },
    "youtube": {
        "name": "YouTube",
        "folder": YOUTUBE_DIR,
        "folder_name": "YouTube",
        "hosts": ("youtube.com", "youtu.be"),
    },
    "douyin": {
        "name": "抖音",
        "folder": DOUYIN_DIR,
        "folder_name": "Douyin",
        "hosts": ("douyin.com", "v.douyin.com", "iesdouyin.com"),
    },
    "mangotv": {
        "name": "芒果TV",
        "folder": MANGOTV_DIR,
        "folder_name": "MangoTV",
        "hosts": ("mgtv.com", "hunantv.com", "mangotv.com"),
    },
}
UNKNOWN_PLATFORM = {
    "name": "Other",
    "folder": OTHER_VIDEO_DIR,
    "folder_name": "Other",
}
BROWSER_CHOICES = {
    "自动": "chrome",
    "Chrome": "chrome",
    "Safari": "safari",
    "Edge": "edge",
    "Firefox": "firefox",
}
VIDEO_TASK_OPTIONS = ["下载视频", "下载并修复", "提取字幕", "图文提取模式", "画面文字 OCR", "音频转文字", "下载 + 修复 + 字幕 + OCR + 音频转文字"]
DOWNLOAD_ENGINE_REGISTRY = {
    "YouTube": [
        {"id": "youtube-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
    ],
    "微博": [
        {"id": "weibo-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
        {"id": "weibo-reserved-parser", "name": "Engine B：备用解析器（预留）", "kind": "reserved", "active": False},
    ],
    "抖音": [
        {"id": "douyin-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
        {"id": "douyin-reserved-parser", "name": "Engine B：备用解析器（预留）", "kind": "reserved", "active": False},
        {"id": "douyin-browser-assist", "name": "Engine C：浏览器抓流/手动辅助模式（预留）", "kind": "reserved", "active": False},
    ],
    "小红书": [
        {"id": "xhs-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
        {"id": "xhs-reserved-parser", "name": "Engine B：备用解析器（预留）", "kind": "reserved", "active": False},
    ],
    "B站": [
        {"id": "bilibili-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
    ],
    "芒果TV": [
        {"id": "mangotv-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
    ],
    "Other": [
        {"id": "other-ytdlp", "name": "Engine A：yt-dlp", "kind": "yt-dlp", "active": True},
    ],
}


class ACANCreatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._configure_embedded_environment()

        self.log_queue = queue.Queue()
        self.worker_thread = None
        self.settings = self._load_settings()
        self.last_command_text = ""
        self.last_final_url = ""
        self.last_platform_name = "Other"
        self.task_mode_var = ctk.StringVar(value="下载视频")
        self._visible_log_lines = 0
        self._max_visible_log_lines = 2500
        self._background_resize_after_id = None
        self._last_background_size = None

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title(APP_NAME)
        self.geometry("920x680")
        self.minsize(820, 620)

        self._prepare_folders()
        self._build_ui()
        self._write_log("欢迎使用 ACAN Studio")
        self._write_log(f"素材库位置：{CREATOR_DIR}")
        self._poll_log_queue()
        self.after(300, self._check_required_tools_on_startup)
        self.after(900, self._maybe_show_dependency_wizard)

    def _build_ui(self):
        build_ui_v2(self, APP_NAME, VIDEO_TASK_OPTIONS)

    def _large_button(self, parent, title, detail, command):
        button = ctk.CTkButton(
            parent,
            text=f"{title}\n{detail}",
            height=116,
            corner_radius=18,
            fg_color=("#F7F7FA", "#252833"),
            hover_color=("#ECEEF5", "#303443"),
            border_width=1,
            border_color=("#D9DCE6", "#4B5264"),
            text_color=("#12131A", "#F7F8FA"),
            font=ctk.CTkFont(size=17, weight="bold"),
            command=command,
        )
        return button

    def _task_button(self, title, mode):
        return self._small_button(
            self.quick_task_frame,
            title,
            lambda selected_mode=mode: self._run_task_mode(selected_mode),
            height=44,
        )

    def _run_task_mode(self, mode):
        self.task_mode_var.set(mode)
        self.download_video()

    def _small_button(self, parent, title, command, height=34):
        return ctk.CTkButton(
            parent,
            text=title,
            height=height,
            corner_radius=14,
            fg_color=("#F7F7FA", "#252833"),
            hover_color=("#ECEEF5", "#303443"),
            border_width=1,
            border_color=("#D9DCE6", "#4B5264"),
            text_color=("#12131A", "#F7F8FA"),
            command=command,
        )

    @staticmethod
    def _card_frame(parent, corner_radius=18):
        return ctk.CTkFrame(
            parent,
            corner_radius=corner_radius,
            fg_color=("#F4F5F8", "#171A22"),
            border_width=1,
            border_color=("#D4D8E3", "#3A4152"),
        )

    @staticmethod
    def _subtle_panel(parent):
        return ctk.CTkFrame(
            parent,
            corner_radius=14,
            fg_color=("#FAFAFC", "#20242E"),
            border_width=1,
            border_color=("#D9DCE6", "#444B5D"),
        )

    def _on_background_configure(self, _event=None):
        if self._background_resize_after_id:
            self.after_cancel(self._background_resize_after_id)
        self._background_resize_after_id = self.after(180, self._resize_background_image)

    def _load_background_image(self):
        self.background_pil_image = None
        self.background_photo_image = None
        self._last_background_size = None
        path_text = getattr(self, "background_image_path", "") or self.settings.get("background_image_path", "") or ""
        self.background_image_path = path_text.strip()
        if not self.background_image_path:
            self._clear_background_label_image()
            return

        image_path = Path(self.background_image_path).expanduser()
        if not image_path.is_file():
            self.background_image_path = ""
            self.settings["background_image_path"] = ""
            self._save_settings()
            self._clear_background_label_image()
            if hasattr(self, "log_text"):
                self._write_log("背景图片文件不存在，已恢复默认背景。")
            return

        try:
            self.background_pil_image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            self.background_pil_image = None
            self._clear_background_label_image()
            if hasattr(self, "log_text"):
                self._write_log(f"背景图片加载失败，已恢复默认背景：{exc}")

    def set_background_image(self, path):
        self.background_image_path = str(path or "").strip()
        self.settings["background_image_path"] = self.background_image_path
        self._save_settings()
        self._load_background_image()
        self._resize_background_image()

    def _clear_background_label_image(self):
        self._last_background_size = None
        if hasattr(self, "background_label"):
            self.background_label.configure(image="", bg="#090B10")
            self.background_label.image = None

    def _resize_background_image(self):
        self._background_resize_after_id = None
        if not hasattr(self, "background_label"):
            return

        if not getattr(self, "background_pil_image", None):
            self._clear_background_label_image()
            return

        width = self.winfo_width()
        height = self.winfo_height()
        if width < 10 or height < 10:
            self.after(100, self._resize_background_image)
            return

        width = max(1, int(width))
        height = max(1, int(height))
        if self._last_background_size == (width, height) and self.background_photo_image:
            return
        self._last_background_size = (width, height)

        try:
            image_width, image_height = self.background_pil_image.size
            scale = max(width / image_width, height / image_height)
            resized_width = max(1, int(image_width * scale))
            resized_height = max(1, int(image_height * scale))
            resized = self.background_pil_image.resize((resized_width, resized_height), Image.LANCZOS)
            left = max(0, (resized_width - width) // 2)
            top = max(0, (resized_height - height) // 2)
            background_image = resized.crop((left, top, left + width, top + height))

            self.background_photo_image = ImageTk.PhotoImage(background_image)
            self.background_label.configure(image=self.background_photo_image, bg="#090B10")
            self.background_label.image = self.background_photo_image
        except Exception as exc:
            self._clear_background_label_image()
            if hasattr(self, "log_text"):
                self._write_log(f"背景图片渲染失败，已恢复默认背景：{exc}")

    def _background_image_path(self):
        return (getattr(self, "background_image_path", "") or self.settings.get("background_image_path") or "").strip()

    def _on_scroll_canvas_configure(self, event):
        if hasattr(self, "content_window"):
            self.scroll_canvas.itemconfigure(self.content_window, width=event.width)

    def _on_scrollable_frame_configure(self, _event=None):
        if hasattr(self, "scroll_canvas"):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _scroll_canvas_yview(self, *args):
        if hasattr(self, "scroll_canvas"):
            self.scroll_canvas.yview(*args)

    def _bind_main_scroll_widgets(self):
        """Bind one lightweight global wheel handler for the main page.

        Older UI experiments recursively bound MouseWheel to every child widget,
        which made the app feel sticky after repeated rebuilds. This version binds
        once and lets _on_mousewheel decide whether the pointer is over the page.
        """
        if getattr(self, "_main_scroll_bound", False):
            return
        self._main_scroll_bound = True
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _on_mousewheel(self, event):
        if not hasattr(self, "scroll_canvas"):
            return
        if not self._pointer_is_over_scroll_canvas():
            return
        if self._event_is_inside_widget(event, getattr(self, "log_text", None)):
            return

        if getattr(event, "num", None) == 4:
            scroll_units = -8
        elif getattr(event, "num", None) == 5:
            scroll_units = 8
        else:
            delta = getattr(event, "delta", 0)
            scroll_units = int(-delta / 4) if delta else 0
            if scroll_units == 0 and delta:
                scroll_units = -1 if delta > 0 else 1

        if scroll_units:
            self.scroll_canvas.yview_scroll(scroll_units, "units")

    def _pointer_is_over_scroll_canvas(self):
        pointer_x = self.winfo_pointerx()
        pointer_y = self.winfo_pointery()
        canvas_x = self.scroll_canvas.winfo_rootx()
        canvas_y = self.scroll_canvas.winfo_rooty()
        return (
            canvas_x <= pointer_x <= canvas_x + self.scroll_canvas.winfo_width()
            and canvas_y <= pointer_y <= canvas_y + self.scroll_canvas.winfo_height()
        )

    @staticmethod
    def _event_is_inside_widget(event, widget):
        if not widget:
            return False
        widget_path = str(widget)
        event_widget = getattr(event, "widget", None)
        while event_widget is not None:
            if str(event_widget).startswith(widget_path):
                return True
            event_widget = getattr(event_widget, "master", None)
        return False

    def choose_background_image(self):
        selected = filedialog.askopenfilename(
            title="选择背景图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp"),
                ("PNG", "*.png"),
                ("JPG", "*.jpg *.jpeg"),
                ("WebP", "*.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if not selected:
            return
        self.set_background_image(selected)
        self._write_log(f"背景图片已设置：{selected}")

    def clear_background_image(self):
        self.background_image_path = ""
        self.settings["background_image_path"] = ""
        self._save_settings()
        self.background_pil_image = None
        self.background_photo_image = None
        self._clear_background_label_image()
        self._write_log("已清除背景图片")

    def _load_settings(self):
        defaults = {
            "settings_version": SETTINGS_VERSION,
            "download_dir": str(CREATOR_DIR),
            "browser": "自动",
            "use_browser_cookie": False,
            "cookie_source": "不使用",
            "cookies_txt": "",
            "background_image_path": "",
            "install_wizard_dismissed": False,
        }
        try:
            if SETTINGS_PATH.exists():
                with SETTINGS_PATH.open("r", encoding="utf-8") as file:
                    saved = json.load(file)
                defaults.update({key: value for key, value in saved.items() if key in defaults})
                try:
                    saved_version = int(saved.get("settings_version", 1))
                except (TypeError, ValueError):
                    saved_version = 1
                if saved_version < SETTINGS_VERSION:
                    defaults["use_browser_cookie"] = False
                    defaults["cookie_source"] = "不使用"
        except Exception:
            pass
        return defaults

    def _save_settings(self):
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_PATH.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, ensure_ascii=False, indent=2)

    def _download_root(self):
        return Path(self.settings.get("download_dir") or str(CREATOR_DIR)).expanduser()

    def _destination_for_platform(self, platform):
        return self._download_root() / platform["folder_name"]

    def _video_dir_for_platform(self, platform):
        platform_root = self._destination_for_platform(platform)
        if platform["name"] == "Other":
            return platform_root
        return platform_root / VIDEO_DIR_NAME

    def _asset_dir_for_platform(self, platform, folder_name):
        platform_root = self._destination_for_platform(platform)
        if platform["name"] == "Other":
            return platform_root
        return platform_root / folder_name

    def _cookie_args(self):
        cookie_source = self.settings.get("cookie_source", "浏览器")
        cookies_txt = self.settings.get("cookies_txt", "").strip()
        if cookie_source == "Cookies.txt" and cookies_txt and Path(cookies_txt).expanduser().is_file():
            return ["--cookies", str(Path(cookies_txt).expanduser())]

        if cookie_source != "浏览器" or not self.settings.get("use_browser_cookie", False):
            return []

        browser_label = self.settings.get("browser", "自动")
        browser = BROWSER_CHOICES.get(browser_label, "chrome")
        return ["--cookies-from-browser", browser]

    def open_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("设置")
        dialog.geometry("620x650")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(dialog, text="设置", font=ctk.CTkFont(size=22, weight="bold"), anchor="w")
        title.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 18))

        dir_frame = ctk.CTkFrame(dialog, corner_radius=14)
        dir_frame.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        dir_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dir_frame, text="下载目录", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=16, pady=14)
        dir_value = ctk.CTkLabel(dir_frame, text=self.settings["download_dir"], text_color=("gray35", "gray70"), anchor="w")
        dir_value.grid(row=0, column=1, sticky="ew", padx=(8, 12), pady=14)

        def choose_dir():
            selected = filedialog.askdirectory(title="选择下载目录", initialdir=self.settings["download_dir"])
            if selected:
                self.settings["download_dir"] = selected
                dir_value.configure(text=selected)
                self._save_settings()
                self._prepare_folders()
                if hasattr(self, "library_path_label"):
                    self.library_path_label.configure(text=f"素材库路径：{self._download_root()}")
                if hasattr(self, "hero_library_label"):
                    self.hero_library_label.configure(text=f"素材库位置：{self._download_root()}")
                self._write_log(f"下载目录已更新：{selected}")

        ctk.CTkButton(dir_frame, text="选择", width=74, command=choose_dir).grid(row=0, column=2, padx=(0, 16), pady=14)

        background_frame = ctk.CTkFrame(dialog, corner_radius=14)
        background_frame.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        background_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(background_frame, text="背景图片", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=16, pady=14)
        background_value = ctk.CTkLabel(
            background_frame,
            text=self._background_image_path() or "未选择背景图片",
            text_color=("gray35", "gray70"),
            anchor="w",
        )
        background_value.grid(row=0, column=1, sticky="ew", padx=(8, 12), pady=14)

        def choose_background():
            self.choose_background_image()
            background_value.configure(text=self._background_image_path() or "未选择背景图片")

        def clear_background():
            self.clear_background_image()
            background_value.configure(text="未选择背景图片")

        ctk.CTkButton(background_frame, text="选择背景图片", width=110, command=choose_background).grid(row=0, column=2, padx=(0, 8), pady=14)
        ctk.CTkButton(
            background_frame,
            text="清除",
            width=64,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=clear_background,
        ).grid(row=0, column=3, padx=(0, 16), pady=14)

        cookie_frame = ctk.CTkFrame(dialog, corner_radius=14)
        cookie_frame.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 14))
        cookie_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cookie_frame, text="Cookie来源", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8))

        browser_var = ctk.StringVar(value=self.settings.get("browser", "自动"))
        ctk.CTkLabel(cookie_frame, text="浏览器").grid(row=1, column=0, sticky="w", padx=16, pady=8)
        browser_menu = ctk.CTkOptionMenu(cookie_frame, values=list(BROWSER_CHOICES.keys()), variable=browser_var)
        browser_menu.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=8)

        cookie_source_var = ctk.StringVar(value=self.settings.get("cookie_source", "不使用"))
        ctk.CTkLabel(cookie_frame, text="Cookie来源").grid(row=2, column=0, sticky="w", padx=16, pady=8)
        cookie_source_menu = ctk.CTkSegmentedButton(cookie_frame, values=["不使用", "浏览器", "Cookies.txt"], variable=cookie_source_var)
        cookie_source_menu.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(8, 16), pady=8)

        cookies_value = ctk.CTkLabel(
            cookie_frame,
            text=self.settings.get("cookies_txt") or "未导入 Cookies.txt",
            text_color=("gray35", "gray70"),
            anchor="w",
        )
        cookies_value.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 14))

        def import_cookies():
            selected = filedialog.askopenfilename(title="选择 Cookies.txt", filetypes=[("Cookies.txt", "*.txt"), ("所有文件", "*.*")])
            if selected:
                self.settings["cookies_txt"] = selected
                self.settings["cookie_source"] = "Cookies.txt"
                cookie_source_var.set("Cookies.txt")
                cookies_value.configure(text=selected)
                self._save_settings()
                self._write_log(f"已导入 Cookies.txt：{selected}")

        ctk.CTkButton(cookie_frame, text="导入Cookies.txt", width=118, command=import_cookies).grid(row=3, column=2, sticky="e", padx=(0, 16), pady=(8, 14))

        def save_and_close():
            self.settings["browser"] = browser_var.get()
            self.settings["cookie_source"] = cookie_source_var.get()
            self.settings["use_browser_cookie"] = cookie_source_var.get() == "浏览器"
            self._save_settings()
            self._write_log("设置已保存")
            self._check_required_tools_on_startup(show_popup=False)
            dialog.destroy()

        env_manage_frame = ctk.CTkFrame(dialog, corner_radius=14)
        env_manage_frame.grid(row=4, column=0, sticky="ew", padx=28, pady=(0, 14))
        env_manage_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(env_manage_frame, text="环境管理", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))
        ctk.CTkButton(env_manage_frame, text="重新检测", command=self.check_backend_tools).grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=8)
        ctk.CTkButton(env_manage_frame, text="重新安装 OCR", command=lambda: self._show_dependency_wizard([("ocr", "OCR 文字识别（Tesseract）", "用于识别视频画面中的文字。")])).grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=8)
        ctk.CTkButton(env_manage_frame, text="重新安装 Whisper", command=lambda: self._show_dependency_wizard([("whisper", "AI 语音识别（Whisper）", "用于采访、直播、无字幕视频转文字。")])).grid(row=2, column=0, sticky="ew", padx=(16, 8), pady=(0, 14))
        ctk.CTkButton(env_manage_frame, text="打开安装说明", command=lambda: webbrowser.open("https://brew.sh")).grid(row=2, column=1, sticky="ew", padx=(8, 16), pady=(0, 14))

        ctk.CTkButton(dialog, text="保存", height=38, command=save_and_close).grid(row=5, column=0, sticky="ew", padx=130, pady=(0, 10))
        ctk.CTkLabel(dialog, text="未来扩展：AI字幕 / AI提取金句 / AI采访整理 / AI脚本生成 / AI封面生成", text_color=("gray42", "gray62")).grid(row=6, column=0, sticky="ew", padx=28, pady=(2, 18))

    def download_video(self):
        user_text = self.url_entry.get("1.0", "end").strip()
        url = self._extract_first_url(user_text)
        if not url:
            self._show_error("没有检测到有效的视频链接。")
            return

        mode = self.task_mode_var.get() or "下载视频"
        platform = self._detect_platform(url)
        original_url = url
        resolved_url = self._resolve_redirect_url(url, platform) if self._should_resolve_redirect(url, platform) else url
        original_platform = platform
        platform = self._detect_platform(resolved_url)
        download_url = resolved_url
        if original_platform["name"] == "芒果TV":
            # MangoTV may redirect a non-browser request to the same landing page
            # for unrelated videos. The playback URL pasted by the user is safer.
            platform = original_platform
            if resolved_url != original_url:
                self._write_log("检测到芒果TV链接跳转，已忽略跳转结果，继续使用原始播放页链接下载。")
            resolved_url = original_url
            download_url = original_url
        if original_platform["name"] == "微博" and self._is_weibo_visitor_url(resolved_url):
            platform = original_platform
            resolved_url = original_url
            download_url = original_url
            self._write_log("检测到微博跳转 visitor，已忽略 visitor，继续使用原始微博链接下载。")

        content_type = self._classify_content_type(download_url, platform)
        if hasattr(self, "content_type_label"):
            self.content_type_label.configure(text=f"内容类型：{CONTENT_TYPE_MESSAGES.get(content_type, '未知')}")
        self.last_final_url = download_url
        self.last_platform_name = platform["name"]
        self._write_parse_block(user_text, original_url, download_url, platform["name"], content_type)
        if resolved_url != original_url:
            self._write_log(f"实际跳转后的链接：{resolved_url}")
        self._write_log(f"内容类型：{CONTENT_TYPE_MESSAGES.get(content_type, '未知')}")

        if platform["name"] == "抖音" and self._is_douyin_jingxuan_url(download_url):
            self._write_log(f"检测到抖音精选页链接，已停止下载：{original_url}")
            self._show_error(DOUYIN_JINGXUAN_ERROR_MESSAGE)
            return

        platform_root = self._destination_for_platform(platform)
        destination_dir = self._video_dir_for_platform(platform)
        fixed_dir = self._asset_dir_for_platform(platform, FIXED_DIR_NAME)
        subtitle_dir = self._asset_dir_for_platform(platform, SUBTITLE_DIR_NAME)
        ocr_dir = self._asset_dir_for_platform(platform, OCR_DIR_NAME)
        transcript_dir = self._asset_dir_for_platform(platform, TRANSCRIPT_DIR_NAME)
        note_dir = self._asset_dir_for_platform(platform, NOTE_DIR_NAME)
        for folder in (platform_root, destination_dir, fixed_dir, subtitle_dir, ocr_dir, transcript_dir, note_dir):
            folder.mkdir(parents=True, exist_ok=True)

        if content_type == "note" or mode == "图文提取模式":
            note_path = self._save_note_content(platform, original_url, resolved_url, user_text, note_dir)
            self._write_log(f"图文/笔记内容已保存：{note_path}")
            self._show_info("这是图文/笔记内容，已保存到图文提取目录。")
            self._open_finder(note_path)
            return

        if content_type in ("live", "collection", "profile"):
            message = f"当前内容类型是{CONTENT_TYPE_MESSAGES[content_type]}，不是普通视频，请使用对应整理模式。"
            self._write_log(f"中文建议：{message}")
            self._show_error(message)
            return

        command_attempts = self._build_download_attempts(platform, download_url, destination_dir)
        subtitle_attempts = self._build_subtitle_attempts(platform, download_url, subtitle_dir)

        if mode == "提取字幕":
            self._prepare_copy_command(subtitle_attempts[-1][1])
        elif platform["name"] == "微博":
            self._prepare_copy_command(command_attempts[0][1])
        else:
            self._prepare_copy_command(command_attempts[-1][1])
        self._run_video_workflow(
            mode=mode,
            platform=platform,
            url=download_url,
            command_attempts=command_attempts,
            subtitle_attempts=subtitle_attempts,
            destination_dir=destination_dir,
            fixed_dir=fixed_dir,
            subtitle_dir=subtitle_dir,
            ocr_dir=ocr_dir,
            transcript_dir=transcript_dir,
            source_url=download_url,
        )

    def _build_download_attempts(self, platform, url, destination_dir):
        engine = self._select_download_engine(platform, self._classify_content_type(url, platform))
        self._write_log(f"下载引擎：{engine['name']}")
        return self._build_yt_dlp_download_attempts(platform, url, destination_dir, engine)

    def _select_download_engine(self, platform, content_type):
        engines = DOWNLOAD_ENGINE_REGISTRY.get(platform["name"]) or DOWNLOAD_ENGINE_REGISTRY["Other"]
        for engine in engines:
            if engine.get("active"):
                return engine
        return engines[0]

    def _youtube_javascript_args(self, platform):
        if platform["name"] != "YouTube":
            return []

        deno_path = self._find_tool("deno")
        if not deno_path:
            return []
        return ["--js-runtimes", f"deno:{deno_path}"]

    def _youtube_network_args(self, platform, chunk_size, retries):
        return build_youtube_network_args(platform, chunk_size, retries)

    @staticmethod
    def _system_proxy_url():
        try:
            proxies = getproxies()
        except (OSError, ValueError):
            return ""

        for proxy_type in ("https", "http", "all"):
            proxy_url = (proxies.get(proxy_type) or "").strip()
            if proxy_url:
                return proxy_url
        return ""

    def _build_yt_dlp_download_attempts(self, platform, url, destination_dir, engine):
        return build_yt_dlp_download_attempts(
            platform,
            url,
            destination_dir,
            engine,
            cookie_args=self._cookie_args(),
            deno_path=self._find_tool("deno"),
            curl_path=self._find_tool("curl"),
            proxy_url=self._system_proxy_url(),
        )

    @staticmethod
    def _clean_url_parameters(url):
        return clean_url_parameters(url)

    def _build_subtitle_attempts(self, platform, url, subtitle_dir):
        subtitle_template = str(subtitle_dir / "%(uploader|未知作者).100B" / "%(upload_date|未知日期)s_%(title).200B.%(ext)s")
        javascript_args = self._youtube_javascript_args(platform)
        base_command = [
            "yt-dlp",
            *javascript_args,
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            "zh-Hans,zh-CN,zh,en",
            "--convert-subs",
            "srt",
            "-o",
            subtitle_template,
            url,
        ]

        if platform["name"] == "抖音":
            return [
                ("字幕提取：使用 Chrome Cookie", ["yt-dlp", "--cookies-from-browser", "chrome", *base_command[1:]]),
                ("字幕提取：不使用 Cookie", base_command),
            ]

        cookie_args = self._cookie_args()
        return [
            ("提取字幕", ["yt-dlp", *cookie_args, *base_command[1:]] if cookie_args else base_command),
        ]

    @staticmethod
    def _should_resolve_redirect(url, platform):
        lowered_url = (url or "").lower()
        short_hosts = ("v.douyin.com", "xhslink.com", "b23.tv", "m.weibo.cn", "youtu.be")
        return platform["name"] in ("抖音", "小红书", "微博", "YouTube", "B站") or any(host in lowered_url for host in short_hosts)

    @staticmethod
    def _classify_content_type(url, platform):
        return classify_content_type(url, platform["name"])

    @staticmethod
    def _mode_needs_download(mode):
        return mode in (
            "下载视频",
            "下载并修复",
            "画面文字 OCR",
            "提取画面文字",
            "音频转文字",
            "下载 + 修复 + 字幕 + OCR + 音频转文字",
            "下载 + 修复 + 提取字幕 + 提取画面文字",
        )

    @staticmethod
    def _mode_needs_fix(mode):
        return mode in ("下载并修复", "下载 + 修复 + 字幕 + OCR + 音频转文字", "下载 + 修复 + 提取字幕 + 提取画面文字")

    @staticmethod
    def _mode_needs_subtitles(mode):
        return mode in ("提取字幕", "下载 + 修复 + 字幕 + OCR + 音频转文字", "下载 + 修复 + 提取字幕 + 提取画面文字")

    @staticmethod
    def _mode_needs_ocr(mode):
        return mode in ("画面文字 OCR", "提取画面文字", "下载 + 修复 + 字幕 + OCR + 音频转文字", "下载 + 修复 + 提取字幕 + 提取画面文字")

    @staticmethod
    def _mode_needs_transcript(mode):
        return mode in ("音频转文字", "下载 + 修复 + 字幕 + OCR + 音频转文字")

    def _run_video_workflow(self, mode, platform, url, command_attempts, subtitle_attempts, destination_dir, fixed_dir, subtitle_dir, ocr_dir, transcript_dir, source_url):
        if self.worker_thread and self.worker_thread.is_alive():
            self._show_error("当前已有任务正在执行，请稍等完成后再操作。")
            return

        required_tools = ["yt-dlp"]
        if platform["name"] == "YouTube":
            required_tools.append("deno")
        if self._mode_needs_download(mode):
            required_tools.append("ffprobe")
        should_fix = self._mode_needs_fix(mode) or (platform["name"] == "YouTube" and mode == "下载视频")
        if should_fix or self._mode_needs_ocr(mode) or self._mode_needs_subtitles(mode) or self._mode_needs_transcript(mode):
            required_tools.append("ffmpeg")
        ocr_engine = self._detect_ocr_engine() if self._mode_needs_ocr(mode) else None
        transcript_engine = self._detect_transcript_engine() if self._mode_needs_transcript(mode) else None

        tool_paths = {}
        missing = []
        for tool in required_tools:
            tool_path = self._find_tool(tool)
            if tool_path:
                tool_paths[tool] = tool_path
            else:
                missing.append(tool)

        if missing:
            message = "执行前检查发现缺少依赖：\n" + "\n".join(f"• {item}" for item in missing)
            if "tesseract" in missing:
                message += "\n\nOCR 需要先安装 Tesseract OCR。"
            if "deno" in missing:
                message += "\n\nYouTube 新版播放器需要 Deno JavaScript 运行时。请安装最新版 ACAN Studio，或在源码运行环境中安装 Deno。"
            self._write_log(message)
            self._show_error(message)
            return

        if self._mode_needs_ocr(mode) and not ocr_engine:
            self._log_ocr_engine_status()
            self._show_install_ocr_dialog(
                lambda: self._run_video_workflow(
                    mode,
                    platform,
                    url,
                    command_attempts,
                    subtitle_attempts,
                    destination_dir,
                    fixed_dir,
                    subtitle_dir,
                    ocr_dir,
                    transcript_dir,
                    source_url,
                )
            )
            return

        if self._mode_needs_transcript(mode) and not transcript_engine:
            message = "语音识别未安装，请先安装 Whisper/faster-whisper。"
            self._write_log(f"中文解决建议：{message}")
            self._show_error(message)
            return

        resolved_attempts = self._resolve_attempts(command_attempts, tool_paths)
        subtitle_attempts = self._resolve_attempts(subtitle_attempts, tool_paths)

        self._set_working(True, f"正在执行：{mode}")
        self._set_progress(0, "下载进度：准备开始")
        self._write_log(f"执行方式：{mode}")
        self._write_log(f"当前平台：{platform['name']}")
        self._write_log(f"实际跳转后的链接：{source_url}")
        self._write_log(f"保存位置：{destination_dir}")
        started_at = datetime.now().timestamp()

        self.worker_thread = threading.Thread(
            target=self._video_workflow_worker,
            args=(mode, platform["name"], resolved_attempts, subtitle_attempts, destination_dir, fixed_dir, subtitle_dir, ocr_dir, transcript_dir, started_at, source_url, tool_paths, should_fix, ocr_engine, transcript_engine),
            daemon=True,
        )
        self.worker_thread.start()

    def _video_workflow_worker(self, mode, platform_name, command_attempts, subtitle_attempts, destination_dir, fixed_dir, subtitle_dir, ocr_dir, transcript_dir, started_at, source_url, tool_paths, should_fix, ocr_engine, transcript_engine):
        try:
            downloaded_path = None
            fixed_path = None
            subtitle_txt_files = []
            ocr_path = None
            transcript_paths = []

            if self._mode_needs_download(mode):
                self.log_queue.put(("log", ""))
                ok, output = self._run_attempts(command_attempts, platform_name, mode, "下载", f"正在下载{platform_name}视频", source_url)
                if not ok:
                    return

                downloaded_path = self._extract_downloaded_file(output, destination_dir)
                if downloaded_path:
                    try:
                        if downloaded_path.stat().st_mtime < started_at - 3:
                            self.log_queue.put(("log", f"检测到同一视频已有文件，直接校验：{downloaded_path}"))
                    except OSError:
                        pass
                else:
                    downloaded_path = self._latest_file_since(destination_dir, started_at)

                if not downloaded_path:
                    self.log_queue.put(("error", "下载命令已结束，但本次没有生成新视频文件。为避免误用旧文件，ACAN Studio 已停止后续处理；请查看日志确认 yt-dlp 输出。"))
                    return

                expected_duration = self._extract_expected_duration(output)
                if expected_duration:
                    try:
                        actual_duration = self._get_video_duration_seconds(downloaded_path, tool_paths["ffprobe"])
                    except Exception as exc:
                        self.log_queue.put(("log", f"视频完整性校验暂时无法完成：{exc}"))
                    else:
                        tolerance = max(15.0, expected_duration * 0.02)
                        if actual_duration + tolerance < expected_duration:
                            downloaded_path = self._mark_incomplete_download(downloaded_path, actual_duration)
                            expected_text = self._format_duration(expected_duration)
                            actual_text = self._format_duration(actual_duration)
                            self.log_queue.put(("log", f"完整性校验失败：页面时长 {expected_text}，下载文件仅 {actual_text}"))
                            if platform_name == "芒果TV" and actual_duration <= 330 and expected_duration >= 600:
                                message = (
                                    f"芒果TV只返回了 {actual_text} 的试看流，完整视频应为 {expected_text}。\n\n"
                                    "该文件已保留并标记为不完整，程序不会继续把它当作完整视频处理。"
                                    "请在设置中启用已登录且拥有播放权限的浏览器 Cookie，或导入 Cookies.txt 后重试。"
                                    "如果仍然只有试看时长，说明平台没有向下载器提供完整流，ACAN Studio 不能绕过会员或版权保护。"
                                )
                            else:
                                message = (
                                    f"下载文件不完整：页面时长 {expected_text}，实际文件仅 {actual_text}。\n\n"
                                    "文件已保留并标记为不完整，请检查网络、登录状态后重新下载。"
                                )
                            self.log_queue.put(("error", message))
                            return

                self.log_queue.put(("log", f"下载完成文件：{downloaded_path}"))

            if should_fix:
                self.log_queue.put(("log", "当前执行步骤：转码生成剪映兼容版"))
                self.log_queue.put(("log", "开始修复视频编码：H.264 + AAC MP4"))
                try:
                    fixed_path = self._transcode_to_edit_ready_mp4(downloaded_path, fixed_dir, tool_paths["ffmpeg"])
                except Exception as exc:
                    self.log_queue.put(("error", self._format_stage_error(platform_name, mode, "转码", str(exc), str(exc))))
                    return
                self.log_queue.put(("log", f"已生成剪映兼容版本：{fixed_path}"))

            if self._mode_needs_subtitles(mode):
                self.log_queue.put(("log", "当前执行步骤：提取字幕"))
                subtitle_started_at = datetime.now().timestamp()
                ok, output = self._run_attempts(subtitle_attempts, platform_name, mode, "字幕", f"正在提取{platform_name}字幕", source_url)
                if ok:
                    subtitle_txt_files = self._convert_recent_srt_to_txt(subtitle_dir, subtitle_started_at)
                    if subtitle_txt_files:
                        for path in subtitle_txt_files:
                            self.log_queue.put(("log", f"字幕文本已生成：{path}"))
                    else:
                        no_subtitle_message = "该视频没有字幕，可使用【音频转文字】识别语音内容。"
                        self.log_queue.put(("log", no_subtitle_message))
                        self.log_queue.put(("info", no_subtitle_message))
                elif mode == "提取字幕":
                    return

            if self._mode_needs_ocr(mode):
                self.log_queue.put(("log", "当前执行步骤：提取画面文字"))
                self.log_queue.put(("log", f"OCR 引擎：✓ {ocr_engine['name']}"))
                self.log_queue.put(("log", "开始画面文字 OCR：每隔 2 秒抽取一帧"))
                try:
                    ocr_path = self._extract_ocr_text(downloaded_path, ocr_dir, tool_paths["ffmpeg"], ocr_engine)
                except Exception as exc:
                    self.log_queue.put(("error", self._format_stage_error(platform_name, mode, "OCR", str(exc), str(exc))))
                    return
                self.log_queue.put(("log", f"OCR 文本已生成：{ocr_path}"))

            if self._mode_needs_transcript(mode):
                self.log_queue.put(("log", "当前执行步骤：音频转文字"))
                self.log_queue.put(("log", f"语音识别引擎：✓ {transcript_engine['name']}"))
                try:
                    transcript_paths = self._transcribe_audio_from_video(downloaded_path, transcript_dir, tool_paths["ffmpeg"], transcript_engine)
                except Exception as exc:
                    self.log_queue.put(("error", self._format_stage_error(platform_name, mode, "音频转文字", str(exc), str(exc))))
                    return
                for path in transcript_paths:
                    self.log_queue.put(("log", f"音频转文字已生成：{path}"))

            completion_dir = self._completion_dir_for_mode(mode, destination_dir, subtitle_dir, ocr_dir, transcript_dir)
            reveal_path = (transcript_paths[0] if transcript_paths else None) or fixed_path or ocr_path or (subtitle_txt_files[0] if subtitle_txt_files else downloaded_path) or completion_dir
            self.log_queue.put(("open", str(reveal_path)))
            self.log_queue.put(("log", f"{mode}完成，文件已保存到：{completion_dir}"))
            self.log_queue.put(("done", "完成"))

        except Exception as exc:
            self.log_queue.put(("error", f"发生错误：{exc}"))

    def _run_attempts(self, command_attempts, platform_name, task_name, stage, title, source_url):
        all_outputs = []
        for attempt_index, (attempt_name, command) in enumerate(command_attempts, start=1):
            self.log_queue.put(("log", attempt_name))
            return_code, output = self._run_command_with_log(command)
            if output:
                all_outputs.append(output)
            if platform_name == "芒果TV" and stage == "下载" and self._is_mgtv_svip_access_filtered(output):
                message = (
                    "该视频当前是“SVIP限时抢先看”，Chrome 登录账号没有本片所需的完整播放权限。\n\n"
                    "ACAN Studio 已在下载前停止，不会再保存2分钟试看文件。"
                    "请使用拥有SVIP抢先看权益的账号，或等抢先看期结束后重试。"
                    "程序不能绕过会员、付费或版权权限。"
                )
                self.log_queue.put(("error", message))
                return False, "\n".join(all_outputs).strip()
            if return_code == 0:
                self.log_queue.put(("progress", {"percent": 100, "speed": "", "eta": ""}))
                return True, "\n".join(all_outputs).strip()

            if attempt_index < len(command_attempts):
                self.log_queue.put(("log", f"{attempt_name}失败，准备自动重试。"))
                continue

            combined_output = "\n".join(all_outputs).strip()
            reason = self._extract_error_reason(combined_output)
            self.log_queue.put(("log", "任务失败，完整错误输出已保留在日志窗口。"))
            message = self._format_stage_error(
                platform_name=platform_name,
                task_name=task_name,
                stage=stage,
                reason=reason,
                output=combined_output,
            )
            self.log_queue.put(("error", message))
            return False, combined_output

        return False, "\n".join(all_outputs).strip()

    @staticmethod
    def _extract_expected_duration(output):
        matches = list(YTDLP_EXPECTED_DURATION_PATTERN.finditer(output or ""))
        if not matches:
            return None
        try:
            duration = float(matches[-1].group("duration"))
        except (TypeError, ValueError):
            return None
        return duration if duration > 0 else None

    @staticmethod
    def _extract_downloaded_file(output, destination_dir):
        matches = list(YTDLP_DOWNLOADED_FILE_PATTERN.finditer(output or ""))
        if not matches:
            return None

        candidate = Path(matches[-1].group("path").strip()).expanduser()
        try:
            candidate = candidate.resolve()
            destination_dir = Path(destination_dir).expanduser().resolve()
        except OSError:
            return None

        video_suffixes = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
        if not candidate.is_relative_to(destination_dir):
            return None
        if candidate.suffix.lower() not in video_suffixes or not candidate.is_file():
            return None
        return candidate

    @staticmethod
    def _is_mgtv_svip_access_filtered(output):
        output = output or ""
        return "does not pass filter" in output and MGTV_SVIP_FILTERS[-1] in output

    @staticmethod
    def _mark_incomplete_download(video_path, actual_duration):
        video_path = Path(video_path)
        if re.search(r"_INCOMPLETE_\d+s(?:_\d+)?$", video_path.stem):
            return video_path
        seconds = max(0, int(round(actual_duration)))
        candidate = video_path.with_name(f"{video_path.stem}_INCOMPLETE_{seconds}s{video_path.suffix}")
        index = 2
        while candidate.exists():
            candidate = video_path.with_name(f"{video_path.stem}_INCOMPLETE_{seconds}s_{index}{video_path.suffix}")
            index += 1
        try:
            return video_path.rename(candidate)
        except OSError:
            return video_path

    def _run_command_with_log(self, command):
        output_lines = []
        log_state = {"last_emit_at": 0.0, "pending": ""}
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=self._command_environment(),
        )

        if process.stdout:
            for line in process.stdout:
                clean_line = line.rstrip()
                output_lines.append(clean_line)
                self._queue_command_log_line(clean_line, log_state)
                progress = self._parse_ytdlp_progress(clean_line)
                if progress:
                    self.log_queue.put(("progress", progress))

        self._flush_command_log_line(log_state)
        return process.wait(), "\n".join(output_lines).strip()

    @staticmethod
    def _is_noisy_command_line(line):
        text = (line or "").strip()
        if not text:
            return False
        lowered = text.lower()
        if lowered.startswith("frame="):
            return True
        if lowered.startswith("[download]") and "%" in lowered:
            return True
        return " time=" in lowered and (" bitrate=" in lowered or " speed=" in lowered)

    def _queue_command_log_line(self, line, state, min_interval=0.8):
        clean_line = (line or "").rstrip()
        if not clean_line:
            return

        if not self._is_noisy_command_line(clean_line):
            self._flush_command_log_line(state)
            self.log_queue.put(("log", clean_line))
            return

        now = time.monotonic()
        if now - state.get("last_emit_at", 0.0) >= min_interval:
            state["last_emit_at"] = now
            state["pending"] = ""
            self.log_queue.put(("log", clean_line))
        else:
            state["pending"] = clean_line

    def _flush_command_log_line(self, state):
        pending = state.get("pending")
        if pending:
            state["pending"] = ""
            state["last_emit_at"] = time.monotonic()
            self.log_queue.put(("log", pending))

    @staticmethod
    def _format_stage_error(platform_name, task_name, stage, reason, output):
        suggestion = ACANCreatorApp._platform_stage_suggestion(platform_name, stage, output)
        if platform_name == "微博" and ACANCreatorApp._is_weibo_visitor_error(output):
            reason = "微博跳转到登录/访客验证页。完整英文输出已保留在日志窗口。"
        return (
            f"当前平台：{platform_name}\n"
            f"当前任务：{task_name}\n"
            f"失败阶段：{stage}\n\n"
            f"真实错误原因：\n{reason}\n\n"
            f"中文建议：\n{suggestion}\n\n"
            "完整错误输出已保留在日志窗口。"
        )

    @staticmethod
    def _platform_stage_suggestion(platform_name, stage, output):
        return platform_stage_suggestion(platform_name, stage, output)

    @staticmethod
    def _is_weibo_visitor_error(output):
        lowered_output = (output or "").lower()
        return any(keyword in lowered_output for keyword in WEIBO_VISITOR_ERROR_KEYWORDS)

    @staticmethod
    def _is_weibo_visitor_url(url):
        lowered_url = (url or "").lower()
        return any(keyword in lowered_url for keyword in WEIBO_VISITOR_URL_KEYWORDS)

    @staticmethod
    def _completion_dir_for_mode(mode, destination_dir, subtitle_dir, ocr_dir, transcript_dir):
        if mode == "音频转文字":
            return transcript_dir
        if mode in ("画面文字 OCR", "提取画面文字"):
            return ocr_dir
        if mode == "提取字幕":
            return subtitle_dir
        return destination_dir

    def _transcode_to_edit_ready_mp4(self, input_path, fixed_dir, ffmpeg_path):
        output_path = self._fixed_video_path(input_path, fixed_dir)
        command = [
            ffmpeg_path,
            "-y",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        return_code, output = self._run_command_with_log(command)
        if return_code != 0:
            reason = self._extract_error_reason(output)
            raise RuntimeError(f"视频修复失败：\n{reason}")
        return output_path

    def _extract_ocr_text(self, video_path, destination_dir, ffmpeg_path, ocr_engine):
        try:
            from PIL import Image
        except Exception as exc:
            raise RuntimeError(f"OCR 图像依赖不可用：{exc}") from exc

        output_path = destination_dir / OCR_OUTPUT_NAME
        seen = set()
        extracted_lines = []

        with tempfile.TemporaryDirectory(prefix="acan_ocr_") as temp_dir:
            frame_template = str(Path(temp_dir) / "frame_%05d.png")
            command = [
                ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                "fps=1/2",
                frame_template,
            ]
            return_code, output = self._run_command_with_log(command)
            if return_code != 0:
                reason = self._extract_error_reason(output)
                raise RuntimeError(f"OCR 抽帧失败：\n{reason}")

            frames = sorted(Path(temp_dir).glob("frame_*.png"))
            for index, frame in enumerate(frames, start=1):
                self.log_queue.put(("log", f"OCR 识别第 {index}/{len(frames)} 帧"))
                text = self._recognize_frame_text(frame, ocr_engine, Image)

                for line in text.splitlines():
                    cleaned = re.sub(r"\s+", " ", line).strip()
                    if not cleaned:
                        continue
                    key = cleaned.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    extracted_lines.append(cleaned)

        if not extracted_lines:
            extracted_lines.append("未识别到明显的画面文字。")

        output_path.write_text("\n".join(extracted_lines) + "\n", encoding="utf-8")
        return output_path

    def _transcribe_audio_from_video(self, video_path, transcript_dir, ffmpeg_path, transcript_engine):
        transcript_dir.mkdir(parents=True, exist_ok=True)
        video_path = Path(video_path)
        txt_path = self._unique_transcript_path(transcript_dir, video_path.stem, ".txt")
        srt_path = txt_path.with_suffix(".srt")
        self.log_queue.put(("log", f"当前视频文件：{video_path}"))
        self.log_queue.put(("log", f"使用的语音识别引擎：{transcript_engine['name']}"))

        with tempfile.TemporaryDirectory(prefix="acan_transcript_") as temp_dir:
            wav_path = Path(temp_dir) / f"{video_path.stem}.wav"
            self.log_queue.put(("log", f"提取音频路径：{wav_path}"))
            self.log_queue.put(("log", "识别进度：正在提取 16kHz 单声道 WAV"))
            command = [
                ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-acodec",
                "pcm_s16le",
                str(wav_path),
            ]
            return_code, output = self._run_command_with_log(command)
            if return_code != 0:
                reason = self._extract_error_reason(output)
                self.log_queue.put(("log", f"失败原因：{reason}"))
                raise RuntimeError(f"音频提取失败：\n{reason}")

            self.log_queue.put(("log", "识别进度：正在加载语音识别模型"))
            segments = self._run_transcript_engine(wav_path, transcript_engine, ffmpeg_path)
            self.log_queue.put(("log", f"识别进度：识别完成，共 {len(segments)} 个片段"))

        plain_text = "\n".join(segment["text"].strip() for segment in segments if segment["text"].strip())
        if not plain_text:
            plain_text = "未识别到清晰语音内容。"

        txt_path.write_text(plain_text + "\n", encoding="utf-8")
        srt_path.write_text(self._segments_to_srt(segments), encoding="utf-8")
        self.log_queue.put(("log", f"输出文件路径：{txt_path}"))
        self.log_queue.put(("log", f"输出文件路径：{srt_path}"))
        return [txt_path, srt_path]

    def _run_transcript_engine(self, wav_path, transcript_engine, ffmpeg_path=None):
        # OpenAI Whisper internally calls an executable named "ffmpeg".
        # The packaged app may not inherit Homebrew's PATH, so add the detected
        # ffmpeg directory before loading/transcribing.
        if ffmpeg_path:
            try:
                ffmpeg_dir = str(Path(ffmpeg_path).parent)
                current_path = os.environ.get("PATH", "")
                if ffmpeg_dir and ffmpeg_dir not in current_path.split(os.pathsep):
                    os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
            except Exception:
                pass

        if transcript_engine["kind"] == "faster-whisper":
            from faster_whisper import WhisperModel

            if not hasattr(ACANCreatorApp, "_faster_whisper_model"):
                bundled_model = ACANCreatorApp._bundled_whisper_model_dir()
                model_source = str(bundled_model) if bundled_model else "base"
                self.log_queue.put(("log", f"语音识别模型：{'内置 base 模型' if bundled_model else 'base 模型'}"))
                ACANCreatorApp._faster_whisper_model = WhisperModel(model_source, device="cpu", compute_type="int8")

            self.log_queue.put(("log", "识别进度：正在自动识别语言，中文内容会自动识别"))
            segments, info = ACANCreatorApp._faster_whisper_model.transcribe(
                str(wav_path),
                language=None,
                initial_prompt="以下音频可能包含中文采访、口播或普通话内容。",
            )
            collected_segments = []
            for index, segment in enumerate(segments, start=1):
                collected_segments.append({"start": segment.start, "end": segment.end, "text": segment.text})
                if index % 5 == 0:
                    self.log_queue.put(("log", f"识别进度：已识别 {index} 个片段"))
            return collected_segments

        if transcript_engine["kind"] == "whisper-cli":
            return self._run_whisper_cli(wav_path, transcript_engine["path"], ffmpeg_path)

        import whisper

        if not hasattr(ACANCreatorApp, "_whisper_model"):
            ACANCreatorApp._whisper_model = whisper.load_model("base")

        self.log_queue.put(("log", "识别进度：正在自动识别语言，中文内容会自动识别"))
        result = ACANCreatorApp._whisper_model.transcribe(
            str(wav_path),
            language=None,
            task="transcribe",
            initial_prompt="以下音频可能包含中文采访、口播或普通话内容。",
        )
        return [
            {
                "start": float(segment.get("start", 0)),
                "end": float(segment.get("end", 0)),
                "text": segment.get("text", ""),
            }
            for segment in result.get("segments", [])
        ]

    def _run_whisper_cli(self, wav_path, whisper_path, ffmpeg_path=None):
        output_dir = Path(tempfile.mkdtemp(prefix="acan_whisper_cli_"))
        self.log_queue.put(("log", f"识别进度：调用 Whisper 命令行：{whisper_path}"))
        self.log_queue.put(("log", "识别进度：正在自动识别语言，中文内容会自动识别"))

        env = os.environ.copy()
        if ffmpeg_path:
            ffmpeg_dir = str(Path(ffmpeg_path).parent)
            env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

        command = [
            str(whisper_path),
            str(wav_path),
            "--model",
            "base",
            "--task",
            "transcribe",
            "--output_dir",
            str(output_dir),
            "--output_format",
            "all",
            "--initial_prompt",
            "以下音频可能包含中文采访、口播或普通话内容。",
        ]

        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        output = process.stdout or ""
        for line in output.splitlines():
            cleaned = line.strip()
            if cleaned:
                self.log_queue.put(("log", cleaned))

        if process.returncode != 0:
            reason = self._extract_error_reason(output)
            raise RuntimeError(f"Whisper 命令行识别失败：\n{reason}")

        srt_files = sorted(output_dir.glob("*.srt"), key=lambda path: path.stat().st_mtime, reverse=True)
        txt_files = sorted(output_dir.glob("*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)

        if srt_files:
            return self._segments_from_srt(srt_files[0].read_text(encoding="utf-8", errors="ignore"))

        if txt_files:
            text = txt_files[0].read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                return [{"start": 0.0, "end": 1.0, "text": text}]

        return []

    @staticmethod
    def _segments_from_srt(content):
        return segments_from_srt(content)

    @staticmethod
    def _parse_srt_time(value):
        from acan_studio.core.media import parse_srt_time

        return parse_srt_time(value)

    def _recognize_frame_text(self, frame, ocr_engine, image_module):
        if ocr_engine["kind"] == "vision":
            result = subprocess.run(
                [ocr_engine["path"], str(frame)],
                capture_output=True,
                text=True,
                timeout=90,
                env=self._command_environment(),
                check=False,
            )
            if result.returncode != 0:
                reason = (result.stderr or result.stdout or "macOS Vision OCR 未返回错误详情").strip()
                raise RuntimeError(f"macOS Vision OCR 识别失败：{reason}")
            return result.stdout

        if ocr_engine["kind"] == "paddle":
            return self._recognize_frame_with_paddle(frame)

        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = ocr_engine["path"]
        try:
            return pytesseract.image_to_string(image_module.open(frame), lang="chi_sim+eng")
        except Exception:
            return pytesseract.image_to_string(image_module.open(frame))

    @staticmethod
    def _recognize_frame_with_paddle(frame):
        from paddleocr import PaddleOCR

        if not hasattr(ACANCreatorApp, "_paddle_ocr_instance"):
            ACANCreatorApp._paddle_ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch")

        result = ACANCreatorApp._paddle_ocr_instance.ocr(str(frame), cls=True)
        lines = []
        for text in ACANCreatorApp._flatten_paddleocr_result(result):
            if text:
                lines.append(text)
        return "\n".join(lines)

    @staticmethod
    def _flatten_paddleocr_result(result):
        texts = []
        if not result:
            return texts
        if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[0], str):
            return [result[0]]
        if isinstance(result, list):
            for item in result:
                if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (tuple, list)):
                    texts.append(str(item[1][0]))
                elif isinstance(item, list) and len(item) >= 2 and isinstance(item[1], (tuple, list)) and item[1]:
                    texts.append(str(item[1][0]))
                elif isinstance(item, list):
                    texts.extend(ACANCreatorApp._flatten_paddleocr_result(item))
                elif isinstance(item, dict):
                    for key in ("text", "rec_text", "label"):
                        if key in item:
                            texts.append(str(item[key]))
        return texts

    def _convert_recent_srt_to_txt(self, subtitle_dir, started_at):
        txt_files = []
        for srt_path in sorted(Path(subtitle_dir).rglob("*.srt")):
            if srt_path.stat().st_mtime < started_at - 1:
                continue
            text = self._srt_to_plain_text(srt_path.read_text(encoding="utf-8", errors="ignore"))
            txt_path = srt_path.with_suffix(".txt")
            txt_path.write_text(text, encoding="utf-8")
            txt_files.append(txt_path)
        return txt_files

    @staticmethod
    def _srt_to_plain_text(content):
        return srt_to_plain_text(content)

    @staticmethod
    def _segments_to_srt(segments):
        return segments_to_srt(segments)

    @staticmethod
    def _format_srt_time(seconds):
        return format_srt_time(seconds)

    def clear_input(self):
        self.url_entry.delete("1.0", "end")
        self.platform_label.configure(text="识别平台：等待粘贴链接")
        if hasattr(self, "content_type_label"):
            self.content_type_label.configure(text="内容类型：等待识别")
        self._write_log("已清空链接输入框")

    def copy_logs(self):
        logs = self.log_text.get("1.0", "end").strip()
        if not logs:
            self._show_info("日志为空，暂时没有内容可复制。")
            return

        self.clipboard_clear()
        self.clipboard_append(logs)
        self._write_log("日志已复制到剪贴板")

    def copy_command(self):
        if not self.last_command_text:
            self._show_info("暂无可复制的下载命令。请先粘贴链接并开始下载。")
            return

        self.clipboard_clear()
        self.clipboard_append(self.last_command_text)
        self._write_log("下载命令已复制到剪贴板")

    def check_backend_tools(self):
        self._write_log("========== 后台工具检测 ==========")
        self._log_tool_status("yt-dlp", ["yt-dlp", "--version"])
        self._log_tool_status("Deno（YouTube JavaScript）", ["deno", "--version"])
        self._log_tool_status("ffmpeg", ["ffmpeg", "-version"])

        cookie_source = self.settings.get("cookie_source", "不使用")
        if cookie_source == "Cookies.txt":
            cookies_txt = self.settings.get("cookies_txt", "").strip()
            if cookies_txt and Path(cookies_txt).expanduser().is_file():
                self._write_log("Cookies.txt：可读取")
            else:
                self._write_log("Cookies.txt：未找到，请重新导入文件")
        elif cookie_source == "浏览器" and self.settings.get("use_browser_cookie", False):
            browser_label = self.settings.get("browser", "自动")
            display_name = "Chrome" if browser_label == "自动" else browser_label
            if self._browser_available(browser_label):
                self._write_log(f"{display_name} Cookie：已启用，将在下载时验证登录状态")
            else:
                self._write_log(f"{display_name} Cookie：已启用，但未检测到该浏览器")
        else:
            self._write_log("Cookie：未启用（可在设置中主动开启）")

        self._log_ocr_engine_status()
        self._log_transcript_engine_status()
        self._write_log("========== 检测完成 ==========")

    def refresh_cookie_status(self):
        self._write_log("正在重新读取 Cookie 状态...")
        cookie_source = self.settings.get("cookie_source", "不使用")
        if cookie_source == "不使用" or (
            cookie_source == "浏览器" and not self.settings.get("use_browser_cookie", False)
        ):
            message = "Cookie 当前未启用。这是可选功能，不会影响公开视频下载；需要登录下载时再到设置中开启。"
            self._write_log(message)
            self._show_info(message)
            return

        if cookie_source == "浏览器":
            browser_label = self.settings.get("browser", "自动")
            display_name = "Chrome" if browser_label == "自动" else browser_label
            if self._browser_available(browser_label):
                message = f"{display_name} Cookie 已启用。具体登录权限会在下载时验证。"
                self._write_log(message)
                self._show_info(message)
            else:
                message = f"未检测到 {display_name}，请安装或在设置中选择其他浏览器。"
                self._write_log(message)
                self._show_error(message)
            return

        cookie_status = self._cookie_status_ok()
        if cookie_status:
            if cookie_source == "Cookies.txt":
                self._write_log("Cookies.txt：可读取")
                self._show_info("Cookies.txt 可读取。请确认文件来自你有权使用的账号。")
        else:
            if self.settings.get("cookie_source") == "Cookies.txt":
                message = "未找到可读取的 Cookies.txt，请在设置中重新导入文件。"
            else:
                message = "当前未启用 Cookie。需要登录下载时，请在设置中选择浏览器或导入 Cookies.txt。"
            self._write_log(f"中文建议：{message}")
            self._show_error(message)

    def open_current_platform_site(self):
        platform_urls = {
            "抖音": "https://www.douyin.com",
            "小红书": "https://www.xiaohongshu.com",
            "微博": "https://weibo.com",
            "YouTube": "https://www.youtube.com",
            "B站": "https://www.bilibili.com",
            "芒果TV": "https://www.mgtv.com",
        }
        url = platform_urls.get(self.last_platform_name) or self.last_final_url or str(self._download_root())
        webbrowser.open(url)
        self._write_log(f"已打开：{url}")

    def show_detailed_logs(self):
        self.copy_logs()
        self._show_info("完整日志已复制到剪贴板，可以直接粘贴给 ChatGPT 分析。")

    def _log_tool_status(self, tool_name, version_command):
        tool_path = self._find_tool(tool_name)
        if not tool_path:
            self._write_log(f"{tool_name}：未找到")
            return

        self._write_log(f"{tool_name}：{tool_path}")
        try:
            command = [tool_path, *version_command[1:]]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=8,
                env=self._command_environment(),
                check=False,
            )
            output = (result.stdout or result.stderr or "").strip().splitlines()
            if output:
                self._write_log(f"{tool_name} 版本：{output[0]}")
        except Exception as exc:
            self._write_log(f"{tool_name} 版本检测失败：{exc}")

    def extract_mp3(self):
        file_path = filedialog.askopenfilename(
            title="请选择一个视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.mkv *.avi *.m4v *.webm"),
                ("所有文件", "*.*"),
            ],
        )

        if not file_path:
            return

        input_path = Path(file_path)
        output_path = self._unique_audio_path(input_path.stem)

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_path),
        ]

        self._run_task(
            title="正在提取MP3",
            command=command,
            done_message=f"MP3 已生成：{output_path}",
            open_path=output_path,
            required_tools=["ffmpeg"],
        )

    def convert_mp3_to_wav(self):
        file_path = filedialog.askopenfilename(
            title="请选择一个 MP3 音频文件",
            filetypes=[
                ("MP3 音频", "*.mp3"),
                ("所有文件", "*.*"),
            ],
        )

        if not file_path:
            return

        input_path = Path(file_path)
        if input_path.suffix.lower() != ".mp3":
            message = "请选择扩展名为 .mp3 的音频文件。"
            self._write_log(message)
            self._show_error(message)
            return

        output_path = self._unique_audio_path(input_path.stem, ".wav")
        command = build_mp3_to_wav_command("ffmpeg", input_path, output_path)

        self._run_task(
            title="正在转换 MP3 为 WAV",
            command=command,
            done_message=f"WAV 已生成：{output_path}",
            open_path=output_path,
            required_tools=["ffmpeg"],
        )

    def transcribe_local_video(self):
        file_path = filedialog.askopenfilename(
            title="请选择一个需要转文字的视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.mkv *.avi *.m4v *.webm"),
                ("所有文件", "*.*"),
            ],
        )

        if not file_path:
            return

        video_path = Path(file_path)
        platform = self._platform_for_local_path(video_path)
        transcript_dir = self._asset_dir_for_platform(platform, TRANSCRIPT_DIR_NAME)
        transcript_dir.mkdir(parents=True, exist_ok=True)

        self._run_local_transcript_task(video_path, platform, transcript_dir)

    def _run_local_transcript_task(self, video_path, platform, transcript_dir):
        if self.worker_thread and self.worker_thread.is_alive():
            self._show_error("当前已有任务正在执行，请稍等完成后再操作。")
            return

        ffmpeg_path = self._find_tool("ffmpeg")
        if not ffmpeg_path:
            message = "未找到 ffmpeg，无法从视频中提取音频。"
            self._write_log(message)
            self._show_error(message)
            return

        transcript_engine = self._detect_transcript_engine()
        if not transcript_engine:
            message = "语音识别未安装，请先安装 Whisper/faster-whisper。"
            self._write_log(f"中文解决建议：{message}")
            self._show_error(message)
            return

        self._set_working(True, "正在执行：音频转文字")
        self._set_progress(0, "音频转文字：准备开始")
        self._write_log("当前执行步骤：音频转文字")
        self._write_log(f"当前平台：{platform['name']}")
        self._write_log(f"当前视频文件：{video_path}")
        self._write_log(f"保存位置：{transcript_dir}")

        self.worker_thread = threading.Thread(
            target=self._local_transcript_worker,
            args=(video_path, transcript_dir, ffmpeg_path, transcript_engine),
            daemon=True,
        )
        self.worker_thread.start()

    def _local_transcript_worker(self, video_path, transcript_dir, ffmpeg_path, transcript_engine):
        try:
            transcript_paths = self._transcribe_audio_from_video(video_path, transcript_dir, ffmpeg_path, transcript_engine)
            for path in transcript_paths:
                self.log_queue.put(("log", f"音频转文字已生成：{path}"))
            self.log_queue.put(("open", str(transcript_paths[0] if transcript_paths else transcript_dir)))
            self.log_queue.put(("done", "完成"))
        except Exception as exc:
            self.log_queue.put(("error", f"音频转文字失败：{exc}"))

    def compress_video(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self._show_error("当前已有任务正在执行，请稍等完成后再操作。")
            return

        file_paths = filedialog.askopenfilenames(
            title="请选择需要压缩的视频文件（可多选）",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.mkv *.webm *.avi"),
                ("所有文件", "*.*"),
            ],
        )

        if not file_paths:
            return

        target_size_mb = self._choose_compression_target_size()
        if not target_size_mb:
            return

        ffmpeg_path = self._find_tool("ffmpeg")
        if not ffmpeg_path:
            message = "未找到 ffmpeg，无法压缩视频。请先安装 ffmpeg 后再使用。"
            self._write_log(message)
            self._show_error(message)
            return

        ffprobe_path = self._find_tool("ffprobe")
        if not ffprobe_path:
            message = "未找到 ffprobe，无法读取视频时长。请确认 ffmpeg/ffprobe 已正确安装。"
            self._write_log(message)
            self._show_error(message)
            return

        compressed_dir = self._download_root() / COMPRESSED_DIR_NAME
        compressed_dir.mkdir(parents=True, exist_ok=True)

        jobs = []
        low_bitrate_items = []
        try:
            for file_path in file_paths:
                input_path = Path(file_path)
                duration_seconds = self._get_video_duration_seconds(input_path, ffprobe_path)
                video_bitrate_kbps, audio_bitrate_kbps = self._calculate_target_bitrates(
                    target_size_mb=target_size_mb,
                    duration_seconds=duration_seconds,
                )
                output_path = self._unique_compressed_path(compressed_dir, input_path.stem, target_size_mb)
                jobs.append(
                    {
                        "input_path": input_path,
                        "output_path": output_path,
                        "duration_seconds": duration_seconds,
                        "target_size_mb": target_size_mb,
                        "video_bitrate_kbps": video_bitrate_kbps,
                        "audio_bitrate_kbps": audio_bitrate_kbps,
                    }
                )
                if video_bitrate_kbps < 250:
                    low_bitrate_items.append(f"{input_path.name}：{video_bitrate_kbps}k")
        except Exception as exc:
            message = f"读取视频信息失败：{exc}"
            self._write_log(message)
            self._show_error(message)
            return

        if low_bitrate_items:
            should_continue = messagebox.askyesno(
                "目标大小可能过小",
                "以下视频计算出的视频码率低于 250k，画质可能严重下降：\n\n"
                + "\n".join(low_bitrate_items[:8])
                + ("\n……" if len(low_bitrate_items) > 8 else "")
                + "\n\n是否继续压缩？",
            )
            if not should_continue:
                return

        self._set_working(True, "正在压缩视频")
        self._set_progress(0, "压缩视频：准备开始")
        self._write_log("当前执行步骤：按目标大小压缩视频")
        self._write_log(f"目标大小：{target_size_mb:g}MB")
        self._write_log(f"待压缩文件数：{len(jobs)}")
        self._write_log(f"输出文件夹：{compressed_dir}")

        self.worker_thread = threading.Thread(
            target=self._compress_video_worker,
            args=(jobs, ffmpeg_path),
            daemon=True,
        )
        self.worker_thread.start()

    def _choose_compression_target_size(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("设置目标大小")
        dialog.geometry("390x300")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        selected = ctk.StringVar(value="")
        target_var = ctk.StringVar(value="270")

        ctk.CTkLabel(
            dialog,
            text="压缩到多大？",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 8))

        ctk.CTkLabel(
            dialog,
            text="输入每个视频的目标大小，单位 MB。比如 200、270、500。",
            text_color=("gray35", "gray70"),
            wraplength=320,
        ).grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))

        input_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew", padx=44, pady=(0, 12))
        input_frame.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(input_frame, textvariable=target_var, height=38, justify="center")
        entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(input_frame, text="MB", width=42).grid(row=0, column=1, padx=(8, 0))

        quick_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        quick_frame.grid(row=3, column=0, sticky="ew", padx=44, pady=(0, 12))
        for index, value in enumerate((150, 200, 270, 500)):
            quick_frame.grid_columnconfigure(index, weight=1)
            ctk.CTkButton(
                quick_frame,
                text=f"{value}MB",
                height=32,
                command=lambda item=value: target_var.set(str(item)),
            ).grid(row=0, column=index, sticky="ew", padx=3)

        def confirm():
            raw_value = target_var.get().strip().replace("MB", "").replace("mb", "")
            try:
                value = float(raw_value)
            except ValueError:
                messagebox.showerror("输入错误", "请输入数字，例如 200、270、500。")
                return
            if value <= 0:
                messagebox.showerror("输入错误", "目标大小必须大于 0MB。")
                return
            selected.set(str(value))
            dialog.destroy()

        ctk.CTkButton(
            dialog,
            text="开始压缩",
            height=40,
            corner_radius=14,
            command=confirm,
        ).grid(row=4, column=0, sticky="ew", padx=44, pady=(6, 8))

        ctk.CTkButton(
            dialog,
            text="取消",
            height=34,
            corner_radius=14,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=dialog.destroy,
        ).grid(row=5, column=0, sticky="ew", padx=44, pady=(0, 18))

        entry.focus_set()
        dialog.wait_window()

        if not selected.get():
            return None
        return float(selected.get())

    @staticmethod
    def _get_video_duration_seconds(input_path, ffprobe_path):
        command = [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(input_path),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout or "{}")
        duration = float(data.get("format", {}).get("duration", 0))
        if duration <= 0:
            raise ValueError(f"无法读取视频时长：{input_path.name}")
        return duration

    @staticmethod
    def _calculate_target_bitrates(target_size_mb, duration_seconds, audio_bitrate_kbps=64, safety_ratio=0.96):
        return calculate_target_bitrates(target_size_mb, duration_seconds, audio_bitrate_kbps, safety_ratio)

    @staticmethod
    def _format_duration(seconds):
        return format_duration(seconds)

    def _read_video_info(self, input_path, ffprobe_path=None):
        info = {
            "resolution": "未识别",
            "duration": "未识别",
            "size": self._format_file_size(Path(input_path).stat().st_size) if Path(input_path).exists() else "未识别",
        }

        if not ffprobe_path:
            return info

        command = [
            ffprobe_path,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(input_path),
        ]

        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(result.stdout or "{}")
            streams = data.get("streams") or []
            if streams:
                width = streams[0].get("width")
                height = streams[0].get("height")
                if width and height:
                    info["resolution"] = f"{width}x{height}"

            duration = float(data.get("format", {}).get("duration") or 0)
            if duration > 0:
                info["duration"] = self._format_duration(duration)
        except Exception as exc:
            info["duration"] = f"未识别（{exc}）"

        return info

    @staticmethod
    def _format_file_size(size_bytes):
        return format_file_size(size_bytes)

    def _compress_video_worker(self, jobs, ffmpeg_path):
        try:
            total_jobs = len(jobs)
            for index, job in enumerate(jobs, start=1):
                input_path = job["input_path"]
                output_path = job["output_path"]
                target_size_mb = job["target_size_mb"]
                video_bitrate_kbps = job["video_bitrate_kbps"]
                audio_bitrate_kbps = job["audio_bitrate_kbps"]
                duration_seconds = job["duration_seconds"]

                base_percent = int((index - 1) / total_jobs * 100)
                self.log_queue.put(("progress", {"percent": base_percent, "speed": "", "eta": ""}))
                self.log_queue.put(("log", f"[{index}/{total_jobs}] 正在压缩：{input_path.name}"))
                self.log_queue.put(("log", f"目标大小：{target_size_mb:g}MB"))
                self.log_queue.put(("log", f"视频时长：{self._format_duration(duration_seconds)}"))
                self.log_queue.put(("log", f"计算视频码率：{video_bitrate_kbps}k"))
                self.log_queue.put(("log", f"音频码率：{audio_bitrate_kbps}k"))
                self.log_queue.put(("log", f"输出路径：{output_path}"))

                with tempfile.TemporaryDirectory(prefix="acan_ffmpeg_pass_") as temp_dir:
                    passlog_prefix = str(Path(temp_dir) / f"pass_{input_path.stem}")
                    null_output = "NUL" if sys.platform.startswith("win") else "/dev/null"

                    pass1_command = [
                        ffmpeg_path,
                        "-y",
                        "-i",
                        str(input_path),
                        "-map",
                        "0:v:0",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-b:v",
                        f"{video_bitrate_kbps}k",
                        "-pass",
                        "1",
                        "-passlogfile",
                        passlog_prefix,
                        "-an",
                        "-f",
                        "mp4",
                        null_output,
                    ]

                    pass2_command = [
                        ffmpeg_path,
                        "-y",
                        "-i",
                        str(input_path),
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0?",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-b:v",
                        f"{video_bitrate_kbps}k",
                        "-pass",
                        "2",
                        "-passlogfile",
                        passlog_prefix,
                        "-c:a",
                        "aac",
                        "-b:a",
                        f"{audio_bitrate_kbps}k",
                        "-movflags",
                        "+faststart",
                        str(output_path),
                    ]

                    self.log_queue.put(("log", "第一遍：分析视频码率……"))
                    return_code, output = self._run_command_with_log(pass1_command)
                    if return_code != 0:
                        reason = self._extract_error_reason(output)
                        self.log_queue.put(("error", f"压缩视频失败：\n{reason}\n\n完整错误输出已保留在日志窗口。"))
                        return

                    self.log_queue.put(("log", "第二遍：正式压缩导出……"))
                    return_code, output = self._run_command_with_log(pass2_command)
                    if return_code != 0:
                        reason = self._extract_error_reason(output)
                        self.log_queue.put(("error", f"压缩视频失败：\n{reason}\n\n完整错误输出已保留在日志窗口。"))
                        return

                final_size_mb = output_path.stat().st_size / 1024 / 1024 if output_path.exists() else 0
                done_percent = int(index / total_jobs * 100)
                self.log_queue.put(("progress", {"percent": done_percent, "speed": "", "eta": ""}))
                self.log_queue.put(("log", f"压缩完成：{output_path}"))
                self.log_queue.put(("log", f"最终大小：{final_size_mb:.1f}MB"))

            self.log_queue.put(("progress", {"percent": 100, "speed": "", "eta": ""}))
            self.log_queue.put(("open", str(jobs[-1]["output_path"].parent if jobs else self._download_root() / COMPRESSED_DIR_NAME)))
            self.log_queue.put(("done", "完成"))
        except Exception as exc:
            self.log_queue.put(("error", f"压缩视频失败：{exc}"))

    def enhance_video_4k(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self._show_error("当前已有任务正在执行，请稍等完成后再操作。")
            return

        file_paths = filedialog.askopenfilenames(
            title="请选择需要修复画质的视频文件（可多选）",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.mkv *.avi *.m4v *.webm"),
                ("所有文件", "*.*"),
            ],
        )

        if not file_paths:
            return

        mode = self._choose_enhance_mode()
        if not mode:
            return
        if mode == "AI增强（实验功能）":
            self.enhance_video_ai()
            return

        ffmpeg_path = self._find_tool("ffmpeg")
        if not ffmpeg_path:
            message = "未找到 ffmpeg，无法修复画质。请先安装 ffmpeg 后再使用。"
            self._write_log(message)
            self._show_error(message)
            return
        self._write_log("ffmpeg路径：")
        self._write_log(str(ffmpeg_path))

        enhanced_dir = self._download_root() / ENHANCED_DIR_NAME
        enhanced_dir.mkdir(parents=True, exist_ok=True)

        jobs = []
        for file_path in file_paths:
            input_path = Path(file_path)
            output_path = self._unique_enhanced_path(enhanced_dir, input_path.stem)
            jobs.append({"input_path": input_path, "output_path": output_path})

        self._set_working(True, "正在修复画质")
        self._set_progress(0, "修复画质：准备开始")
        self._write_log("当前执行步骤：修复画质4K")
        self._write_log(f"修复模式：{mode}")
        self._write_log(f"待处理文件数：{len(jobs)}")
        self._write_log(f"输出文件夹：{enhanced_dir}")

        self.worker_thread = threading.Thread(
            target=self._enhance_video_worker,
            args=(jobs, ffmpeg_path, mode),
            daemon=True,
        )
        self.worker_thread.start()

    def enhance_video_ai(self):
        message = "AI增强模块未安装，等待 Real-ESRGAN 接入。"
        self._write_log(message)
        self._show_info("AI增强模块将在后续版本接入 Real-ESRGAN。")
        return message

    def _choose_enhance_mode(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("请选择增强模式")
        dialog.geometry("440x340")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        selected = ctk.StringVar(value="4K增强")

        ctk.CTkLabel(
            dialog,
            text="请选择增强模式",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 8))

        ctk.CTkLabel(
            dialog,
            text="快速增强适合普通电视剧素材；4K增强适合影视CUT高清化；AI增强为实验预留。",
            text_color=("gray35", "gray70"),
            wraplength=340,
        ).grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))

        option_menu = ctk.CTkOptionMenu(
            dialog,
            values=["快速增强", "4K增强", "AI增强（实验功能）"],
            variable=selected,
            height=38,
        )
        option_menu.grid(row=2, column=0, sticky="ew", padx=44, pady=(0, 18))

        result = ctk.StringVar(value="")

        def confirm():
            result.set(selected.get())
            dialog.destroy()

        ctk.CTkButton(
            dialog,
            text="开始修复",
            height=40,
            corner_radius=14,
            command=confirm,
        ).grid(row=3, column=0, sticky="ew", padx=44, pady=(6, 8))

        ctk.CTkButton(
            dialog,
            text="取消",
            height=34,
            corner_radius=14,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=dialog.destroy,
        ).grid(row=4, column=0, sticky="ew", padx=44, pady=(0, 18))

        dialog.wait_window()
        return result.get()

    def _enhance_video_worker(self, jobs, ffmpeg_path, mode):
        try:
            total_jobs = len(jobs)
            ffprobe_path = self._find_tool("ffprobe")
            for index, job in enumerate(jobs, start=1):
                input_path = job["input_path"]
                output_path = job["output_path"]
                base_percent = int((index - 1) / total_jobs * 100)
                video_info = self._read_video_info(input_path, ffprobe_path)

                self.log_queue.put(("progress", {"percent": base_percent, "speed": "", "eta": ""}))
                self.log_queue.put(("log", "正在分析视频："))
                self.log_queue.put(("log", f"文件：{input_path.name}"))
                self.log_queue.put(("log", f"分辨率：{video_info['resolution']}"))
                self.log_queue.put(("log", f"时长：{video_info['duration']}"))
                self.log_queue.put(("log", f"文件大小：{video_info['size']}"))
                self.log_queue.put(("log", f"模式：{mode}"))
                self.log_queue.put(("log", f"当前处理：{index}/{total_jobs}"))
                self.log_queue.put(("log", f"[{index}/{total_jobs}] 正在修复画质：{input_path.name}"))
                self.log_queue.put(("log", f"修复模式：{mode}"))
                self.log_queue.put(("log", f"输出路径：{output_path}"))
                mid_percent = int((index - 0.5) / total_jobs * 100)
                self.log_queue.put(("progress", {"percent": mid_percent, "speed": "", "eta": ""}))

                command = self._enhance_ffmpeg_command(ffmpeg_path, input_path, output_path, mode)
                return_code, output = self._run_command_with_log(command)
                if return_code != 0:
                    reason = self._extract_error_reason(output)
                    self.log_queue.put(("error", f"修复画质失败：\n{reason}\n\n完整错误输出已保留在日志窗口。"))
                    return

                done_percent = int(index / total_jobs * 100)
                self.log_queue.put(("progress", {"percent": done_percent, "speed": "", "eta": ""}))
                self.log_queue.put(("log", f"修复完成：{output_path}"))

            enhanced_dir = jobs[-1]["output_path"].parent if jobs else self._download_root() / ENHANCED_DIR_NAME
            self.log_queue.put(("progress", {"percent": 100, "speed": "", "eta": ""}))
            self.log_queue.put(("log", f"修复画质完成，文件已保存到：{enhanced_dir}"))
            self.log_queue.put(("open", str(enhanced_dir)))
            self.log_queue.put(("done", "完成"))
        except Exception as exc:
            self.log_queue.put(("error", f"修复画质失败：{exc}"))

    @staticmethod
    def _enhance_ffmpeg_command(ffmpeg_path, input_path, output_path, mode):
        if mode == "快速增强":
            vf_filter = "hqdn3d=0.8:0.8:3:3,unsharp=3:3:0.4:3:3:0.2"
            preset = "medium"
            crf = "18"
        else:
            vf_filter = "scale=3840:-2:flags=lanczos,hqdn3d=1.5:1.5:6:6,unsharp=5:5:0.8:3:3:0.4"
            preset = "slow"
            crf = "18"

        return [
            ffmpeg_path,
            "-y",
            "-i",
            str(input_path),
            "-vf",
            vf_filter,
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    def _platform_for_local_path(self, path):
        path_text = str(path)
        for platform in DOWNLOAD_PLATFORMS.values():
            marker = f"/{platform['folder_name']}/"
            if marker in path_text:
                return platform
        return UNKNOWN_PLATFORM

    def open_library(self):
        self._prepare_folders()
        library = self._download_root()
        self._open_finder(library)
        self._write_log(f"已打开素材库：{library}")

    def _run_task(self, title, done_message, open_path, required_tools, reveal_latest_from=None, command=None, command_attempts=None, source_url=None):
        if self.worker_thread and self.worker_thread.is_alive():
            self._show_error("当前已有任务正在执行，请稍等完成后再操作。")
            return

        tool_paths = {}
        missing = []
        for tool in required_tools:
            tool_path = self._find_tool(tool)
            if tool_path:
                tool_paths[tool] = tool_path
            else:
                missing.append(tool)

        if missing:
            message = f"未找到工具：{'、'.join(missing)}。请先安装后再使用。"
            self._write_log(message)
            self._show_error(message)
            return

        if command_attempts is None:
            command_attempts = [("执行", command)]

        resolved_attempts = []
        for attempt_name, attempt_command in command_attempts:
            resolved_attempts.append((attempt_name, [tool_paths.get(attempt_command[0], attempt_command[0])] + attempt_command[1:]))

        self._set_working(True, title)
        self._set_progress(0, "下载进度：准备开始")
        self._write_log(title)
        self._write_log(f"保存位置：{open_path.parent if open_path.is_file() else open_path}")
        started_at = datetime.now().timestamp()

        self.worker_thread = threading.Thread(
            target=self._task_worker,
            args=(title, resolved_attempts, done_message, open_path, reveal_latest_from, started_at, source_url),
            daemon=True,
        )
        self.worker_thread.start()

    @staticmethod
    def _resolve_attempts(command_attempts, tool_paths):
        resolved_attempts = []
        for attempt_name, attempt_command in command_attempts:
            resolved_attempts.append((attempt_name, [tool_paths.get(attempt_command[0], attempt_command[0])] + attempt_command[1:]))
        return resolved_attempts

    def _task_worker(self, title, command_attempts, done_message, open_path, reveal_latest_from, started_at, source_url):
        output_lines = []
        full_output = ""
        all_outputs = []

        try:
            for attempt_index, (attempt_name, command) in enumerate(command_attempts, start=1):
                output_lines = []
                log_state = {"last_emit_at": 0.0, "pending": ""}
                self.log_queue.put(("log", attempt_name))
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=self._command_environment(),
                )

                if process.stdout:
                    for line in process.stdout:
                        clean_line = line.rstrip()
                        output_lines.append(clean_line)
                        self._queue_command_log_line(clean_line, log_state)
                        progress = self._parse_ytdlp_progress(clean_line)
                        if progress:
                            self.log_queue.put(("progress", progress))

                self._flush_command_log_line(log_state)
                return_code = process.wait()
                full_output = "\n".join(output_lines).strip()
                if full_output:
                    all_outputs.append(full_output)
                if return_code != 0:
                    if attempt_index < len(command_attempts):
                        self.log_queue.put(("log", f"{attempt_name}失败，准备自动重试。"))
                        continue

                    combined_output = "\n".join(all_outputs).strip() or full_output
                    reason = self._extract_error_reason(combined_output)
                    self.log_queue.put(("log", "任务失败，完整错误输出已保留在日志窗口。"))
                    if "抖音" in title:
                        douyin_error_message = self._classify_douyin_error(combined_output)
                        if douyin_error_message:
                            self.log_queue.put(("error", douyin_error_message))
                            return
                    self.log_queue.put(("error", f"{title}失败：\n{reason}\n\n完整输出请查看日志窗口。"))
                    return

                self.log_queue.put(("progress", {"percent": 100, "speed": "", "eta": ""}))
                break

            reveal_path = self._latest_file_since(reveal_latest_from, started_at) if reveal_latest_from else open_path
            if reveal_path:
                self.log_queue.put(("log", f"已定位文件：{reveal_path}"))
                self.log_queue.put(("open", str(reveal_path)))
            else:
                self.log_queue.put(("open", str(open_path)))
            self.log_queue.put(("log", done_message))
            self.log_queue.put(("done", "完成"))

        except FileNotFoundError:
            self.log_queue.put(("error", "未找到需要的后台工具，请确认已经安装。"))
        except Exception as exc:
            self.log_queue.put(("error", f"发生错误：{exc}"))

    def _poll_log_queue(self):
        processed = 0
        max_events_per_tick = 80
        try:
            while processed < max_events_per_tick:
                event, value = self.log_queue.get_nowait()
                processed += 1

                if event == "log":
                    self._write_log(value)
                elif event == "error":
                    self._write_log(value)
                    self._show_error(value)
                    self._set_working(False, "操作失败")
                elif event == "info":
                    self._write_log(value)
                    self._show_info(value)
                elif event == "douyin_login_error":
                    self._write_log(value)
                    self._show_douyin_login_dialog()
                    self._set_working(False, "操作失败")
                elif event == "douyin_jingxuan_error":
                    self._write_log(value)
                    self._show_error(value)
                    self._set_working(False, "操作失败")
                elif event == "progress":
                    self._apply_progress(value)
                elif event == "open":
                    self._open_finder(Path(value))
                elif event == "done":
                    self._set_working(False, "完成")
                elif event == "ui":
                    value()
        except queue.Empty:
            pass

        if processed >= max_events_per_tick:
            delay = 40
        elif self.worker_thread and self.worker_thread.is_alive():
            delay = 120
        else:
            delay = 450
        self.after(delay, self._poll_log_queue)

    def _write_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self._visible_log_lines += 1
        if self._visible_log_lines > self._max_visible_log_lines:
            trim_count = min(300, self._visible_log_lines - self._max_visible_log_lines)
            self.log_text.delete("1.0", f"{trim_count + 1}.0")
            self._visible_log_lines -= trim_count
        self.log_text.see("end")

    def _write_parse_block(self, raw_input, extracted_url, final_url, platform_name, content_type="unknown"):
        self._write_log("==================")
        self._write_log("原始输入：")
        for line in raw_input.splitlines() or [""]:
            self._write_log(line)
        self._write_log("")
        self._write_log("提取链接：")
        self._write_log(extracted_url)
        self._write_log("")
        self._write_log("最终链接：")
        self._write_log(final_url)
        self._write_log("")
        self._write_log("平台：")
        self._write_log(platform_name)
        self._write_log("")
        self._write_log("内容类型：")
        self._write_log(CONTENT_TYPE_MESSAGES.get(content_type, "未知"))
        self._write_log("==================")

    def _prepare_copy_command(self, command):
        executable = self._find_tool(command[0]) or command[0]
        full_command = [executable, *command[1:]]
        self.last_command_text = " ".join(shlex.quote(item) for item in full_command)
        self._write_log("可复制调试命令：")
        self._write_log(self.last_command_text)

    @staticmethod
    def _parse_ytdlp_progress(line):
        percent_match = YTDLP_PERCENT_PATTERN.search(line)
        if not percent_match:
            return None

        speed_match = YTDLP_SPEED_PATTERN.search(line)
        eta_match = YTDLP_ETA_PATTERN.search(line)
        return {
            "percent": float(percent_match.group("percent")),
            "speed": speed_match.group("speed") if speed_match else "",
            "eta": eta_match.group("eta") if eta_match else "",
        }

    def _apply_progress(self, progress):
        percent = max(0, min(100, float(progress.get("percent", 0))))
        speed = progress.get("speed") or "未知速度"
        eta = progress.get("eta") or "未知"
        self._set_progress(percent / 100, f"下载进度：{percent:.1f}%｜速度：{speed}｜剩余：{eta}")

    def _set_progress(self, value, text):
        self.progress_bar.set(max(0, min(1, value)))
        self.progress_label.configure(text=text)

    def _update_platform_preview(self, _event=None):
        user_text = self.url_entry.get("1.0", "end").strip()
        url = self._extract_first_url(user_text)
        if not url:
            self.platform_label.configure(text="识别平台：等待粘贴链接")
            if hasattr(self, "content_type_label"):
                self.content_type_label.configure(text="内容类型：等待识别")
            return

        platform = self._detect_platform(url)
        self.platform_label.configure(text=f"识别平台：{platform['name']}")

    @staticmethod
    def _extract_first_url(text):
        return extract_first_url(text)

    def _resolve_redirect_url(self, url, platform=None):
        if platform and platform["name"] == "微博":
            return self._resolve_weibo_url_without_following_visitor(url)

        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                },
            )
            with create_https_opener().open(request, timeout=8) as response:
                return response.geturl().strip() or url
        except Exception as exc:
            self._write_log(f"短链解析失败，继续使用原始链接：{exc}")
            return url

    def _resolve_weibo_url_without_following_visitor(self, url):
        class NoRedirectHandler(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                },
            )
            opener = create_https_opener(NoRedirectHandler())
            with opener.open(request, timeout=8):
                pass
            return url
        except HTTPError as exc:
            location = exc.headers.get("Location", "").strip()
            if location and self._is_weibo_visitor_url(location):
                self._write_log("检测到微博跳转 visitor，已忽略 visitor，继续使用原始微博链接下载。")
                return url
            if 300 <= exc.code < 400:
                self._write_log("微博链接存在跳转，已按规则保留原始微博链接下载。")
                return url
            self._write_log(f"微博链接检查失败，继续使用原始链接：{exc}")
            return url
        except Exception as exc:
            self._write_log(f"微博链接检查失败，继续使用原始链接：{exc}")
            return url

    @staticmethod
    def _is_douyin_jingxuan_url(url):
        if not url:
            return False

        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]

        query = parse_qs(parsed.query)
        return host.endswith("douyin.com") and "/jingxuan" in parsed.path and bool(query.get("modal_id"))

    @staticmethod
    def _is_douyin_note_url(url):
        if not url:
            return False
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return host.endswith("douyin.com") and "/note/" in parsed.path

    def _save_note_content(self, platform, original_url, resolved_url, raw_input, note_dir):
        note_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        note_path = note_dir / f"{platform['folder_name'].lower()}_note_{timestamp}.txt"
        content = [
            f"{platform['name']}图文/笔记内容",
            "",
            "原始输入：",
            raw_input,
            "",
            f"原始链接：{original_url}",
            f"跳转后链接：{resolved_url}",
            "",
            "标题：待提取",
            "作者：待提取",
            "正文：当前已保存链接和分享文案，后续可继续接入图文图片抓取。",
        ]
        note_path.write_text("\n".join(content) + "\n", encoding="utf-8")
        return note_path

    def _detect_platform(self, url):
        platform_checks = [
            DOWNLOAD_PLATFORMS["douyin"],
            DOWNLOAD_PLATFORMS["youtube"],
            DOWNLOAD_PLATFORMS["bilibili"],
            DOWNLOAD_PLATFORMS["xiaohongshu"],
            DOWNLOAD_PLATFORMS["weibo"],
            DOWNLOAD_PLATFORMS["mangotv"],
        ]
        return detect_platform(url, platform_checks, UNKNOWN_PLATFORM)

    def _extract_error_reason(self, output):
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return "后台工具没有返回详细错误信息。"

        important_keywords = [
            "ERROR:",
            "Error:",
            "error:",
            "Unsupported URL",
            "HTTP Error",
            "Unable to",
            "unable to",
            "failed",
            "Failed",
            "cookie",
            "Cookie",
            "cookies",
            "Cookies",
            "Sign in",
            "login",
            "Login",
            "ffmpeg",
        ]
        important_lines = [
            line for line in lines
            if any(keyword in line for keyword in important_keywords)
        ]

        reason_lines = important_lines[-8:] if important_lines else lines[-12:]
        reason = "\n".join(reason_lines)

        if len(reason) > 1200:
            return reason[-1200:]
        return reason

    @staticmethod
    def _is_douyin_login_error(output):
        normalized_output = output.lower()
        return any(keyword in normalized_output for keyword in DOUYIN_LOGIN_ERROR_KEYWORDS)

    @staticmethod
    def _classify_douyin_error(output):
        normalized_output = output.lower()
        if any(keyword in normalized_output for keyword in DOUYIN_COOKIE_PARSE_ERROR_KEYWORDS):
            return DOUYIN_YTDLP_COMPAT_ERROR_MESSAGE
        if any(keyword in normalized_output for keyword in DOUYIN_UNSUPPORTED_ERROR_KEYWORDS):
            return DOUYIN_UNSUPPORTED_ERROR_MESSAGE
        if any(keyword in normalized_output for keyword in DOUYIN_LOGIN_ERROR_KEYWORDS):
            return DOUYIN_LOGIN_ERROR_MESSAGE
        if any(keyword in normalized_output for keyword in DOUYIN_NETWORK_ERROR_KEYWORDS):
            return DOUYIN_NETWORK_ERROR_MESSAGE
        return None

    @staticmethod
    def _is_unsupported_url_error(output):
        return "unsupported url" in output.lower()

    @staticmethod
    def _is_login_or_cookie_error(output):
        normalized_output = (output or "").lower()
        keywords = (
            "fresh cookies are needed",
            "failed to parse json",
            "login required",
            "sign in",
            "authentication",
            "cookie",
            "cookies",
        )
        return any(keyword in normalized_output for keyword in keywords)

    def _show_error(self, message):
        messagebox.showerror("提示", message)

    def _show_info(self, message):
        messagebox.showinfo("提示", message)

    def _missing_optional_components(self):
        missing = []
        if not self._detect_ocr_engine():
            missing.append(("ocr", "OCR 文字识别（Tesseract）", "用于识别视频画面中的文字。"))
        if not self._detect_transcript_engine():
            missing.append(("whisper", "AI 语音识别（Whisper）", "用于采访、直播、无字幕视频转文字。"))
        return missing

    def _maybe_show_dependency_wizard(self):
        missing = self._missing_optional_components()
        if not missing:
            self.settings["install_wizard_dismissed"] = False
            self._save_settings()
            return
        if self.settings.get("install_wizard_dismissed"):
            return
        self._show_dependency_wizard(missing)

    def _show_dependency_wizard(self, missing):
        dialog = ctk.CTkToplevel(self)
        dialog.title("安装向导")
        dialog.geometry("560x430")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dialog, text="检测到以下组件未安装：", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="ew", padx=30, pady=(28, 14))

        checks = {}
        list_frame = ctk.CTkFrame(dialog, corner_radius=14)
        list_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 16))
        list_frame.grid_columnconfigure(0, weight=1)

        for index, (key, title, detail) in enumerate(missing):
            var = ctk.BooleanVar(value=True)
            checks[key] = var
            box = ctk.CTkCheckBox(list_frame, text=f"{title}\n{detail}", variable=var)
            box.grid(row=index, column=0, sticky="w", padx=18, pady=14)

        status_label = ctk.CTkLabel(dialog, text="可以一键安装，也可以稍后在设置/工具中重新安装。", text_color=("gray35", "gray70"))
        status_label.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 16))

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(0, 24))
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        install_button = ctk.CTkButton(
            button_frame,
            text="一键安装",
            height=38,
            command=lambda: self._start_dependency_install(dialog, status_label, install_button, checks),
        )
        install_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        later_button = ctk.CTkButton(
            button_frame,
            text="稍后安装",
            height=38,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=lambda: self._dismiss_dependency_wizard(dialog),
        )
        later_button.grid(row=0, column=1, sticky="ew", padx=8)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="取消",
            height=38,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=dialog.destroy,
        )
        cancel_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

    def _dismiss_dependency_wizard(self, dialog):
        self.settings["install_wizard_dismissed"] = True
        self._save_settings()
        dialog.destroy()

    def _start_dependency_install(self, dialog, status_label, install_button, checks):
        selected = [key for key, var in checks.items() if var.get()]
        if not selected:
            self._show_info("请至少选择一个需要安装的组件。")
            return
        install_button.configure(state="disabled", text="正在安装...")
        status_label.configure(text="正在安装，请在日志窗口查看进度。")
        thread = threading.Thread(
            target=self._dependency_install_worker,
            args=(dialog, status_label, install_button, selected),
            daemon=True,
        )
        thread.start()

    def _dependency_install_worker(self, dialog, status_label, install_button, selected):
        success = True
        if "ocr" in selected:
            self.log_queue.put(("log", "正在安装 OCR……"))
            success = self._run_install_command(["brew", "install", "tesseract"]) and success
        if "whisper" in selected:
            self.log_queue.put(("log", "正在安装 AI 语音识别……"))
            success = self._run_install_command([sys.executable, "-m", "pip", "install", "faster-whisper"]) and success

        self.log_queue.put(("ui", lambda: self._finish_dependency_install_ui(dialog, status_label, install_button, success)))

    def _run_install_command(self, command):
        executable = self._find_tool(command[0]) if command[0] == "brew" else command[0]
        if not executable:
            self.log_queue.put(("log", f"未找到安装工具：{command[0]}"))
            return False

        process = subprocess.Popen(
            [executable, *command[1:]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=self._command_environment(),
        )
        if process.stdout:
            for line in process.stdout:
                self.log_queue.put(("log", line.rstrip()))
        return process.wait() == 0

    def _finish_dependency_install_ui(self, dialog, status_label, install_button, success):
        self._check_required_tools_on_startup(show_popup=False)
        missing = self._missing_optional_components()
        if success and not missing:
            self.settings["install_wizard_dismissed"] = False
            self._save_settings()
            self._write_log("✓ OCR 已安装")
            self._write_log("✓ Whisper 已安装")
            dialog.destroy()
            self._show_info("依赖安装完成，环境检测已更新。")
            return

        status_label.configure(text="部分组件仍未安装，请查看日志或稍后重试。")
        install_button.configure(state="normal", text="一键安装")
        self._show_error("部分组件安装失败，请查看日志窗口中的完整输出。")

    def _show_install_ocr_dialog(self, on_success):
        dialog = ctk.CTkToplevel(self)
        dialog.title("提示")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            dialog,
            text="未检测到 OCR 引擎",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 10))

        message = ctk.CTkLabel(
            dialog,
            text="提取画面文字需要 OCR 引擎。\n可以立即安装 Tesseract OCR，安装完成后会自动重新检测并继续识别。",
            font=ctk.CTkFont(size=15),
            text_color=("gray30", "gray75"),
            justify="center",
        )
        message.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 18))

        status_label = ctk.CTkLabel(
            dialog,
            text="OCR 引擎：✗ 未安装",
            font=ctk.CTkFont(size=14),
            text_color=("gray35", "gray70"),
        )
        status_label.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 18))

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", padx=44, pady=(0, 22))
        button_frame.grid_columnconfigure((0, 1), weight=1)

        install_button = ctk.CTkButton(
            button_frame,
            text="立即安装 OCR",
            height=38,
            command=lambda: self._start_ocr_install(dialog, status_label, install_button, on_success),
        )
        install_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        close_button = ctk.CTkButton(
            button_frame,
            text="稍后再说",
            height=38,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=dialog.destroy,
        )
        close_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        dialog.lift()
        dialog.focus_force()

    def _start_ocr_install(self, dialog, status_label, install_button, on_success):
        install_button.configure(state="disabled", text="正在安装...")
        status_label.configure(text="正在安装 Tesseract OCR，请稍候...")
        self._write_log("开始安装 OCR：brew install tesseract")
        thread = threading.Thread(
            target=self._install_ocr_worker,
            args=(dialog, status_label, install_button, on_success),
            daemon=True,
        )
        thread.start()

    def _install_ocr_worker(self, dialog, status_label, install_button, on_success):
        brew_path = self._find_tool("brew")
        if not brew_path:
            self.log_queue.put(("ui", lambda: self._finish_ocr_install_ui(
                dialog,
                status_label,
                install_button,
                on_success,
                False,
                "未找到 Homebrew，无法自动安装 OCR。请先安装 Homebrew，或手动安装 Tesseract。",
            )))
            return

        process = subprocess.Popen(
            [brew_path, "install", "tesseract"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=self._command_environment(),
        )
        output_lines = []
        if process.stdout:
            for line in process.stdout:
                clean_line = line.rstrip()
                output_lines.append(clean_line)
                self.log_queue.put(("log", clean_line))

        return_code = process.wait()
        if return_code == 0 and self._detect_ocr_engine():
            self.log_queue.put(("ui", lambda: self._finish_ocr_install_ui(
                dialog,
                status_label,
                install_button,
                on_success,
                True,
                "OCR 安装完成，正在继续识别。",
            )))
            return

        reason = self._extract_error_reason("\n".join(output_lines))
        self.log_queue.put(("ui", lambda: self._finish_ocr_install_ui(
            dialog,
            status_label,
            install_button,
            on_success,
            False,
            f"OCR 安装失败：\n{reason}",
        )))

    def _finish_ocr_install_ui(self, dialog, status_label, install_button, on_success, success, message):
        self._write_log(message)
        self._log_ocr_engine_status()
        if success:
            dialog.destroy()
            on_success()
            return

        status_label.configure(text="OCR 引擎：✗ 未安装")
        install_button.configure(state="normal", text="立即安装 OCR")
        self._show_error(message)

    def _show_douyin_login_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("提示")
        dialog.geometry("430x230")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            dialog,
            text="抖音下载失败",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 10))

        message = ctk.CTkLabel(
            dialog,
            text="请先在 Chrome 登录 douyin.com，\n再把 App 分享链接粘到 Chrome 打开，\n复制跳转后的网页地址重新下载。",
            font=ctk.CTkFont(size=15),
            text_color=("gray30", "gray75"),
            justify="center",
        )
        message.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 22))

        open_button = ctk.CTkButton(
            dialog,
            text="打开抖音网页版",
            height=38,
            command=lambda: self._open_douyin_web(dialog),
        )
        open_button.grid(row=2, column=0, sticky="ew", padx=44, pady=(0, 10))

        close_button = ctk.CTkButton(
            dialog,
            text="知道了",
            height=34,
            fg_color=("gray82", "gray28"),
            hover_color=("gray74", "gray34"),
            text_color=("gray12", "gray92"),
            command=dialog.destroy,
        )
        close_button.grid(row=3, column=0, sticky="ew", padx=44, pady=(0, 22))

        dialog.lift()
        dialog.focus_force()

    def _open_douyin_web(self, dialog):
        webbrowser.open(DOUYIN_WEB_URL)
        self._write_log(f"已打开抖音网页版：{DOUYIN_WEB_URL}")
        dialog.destroy()

    def _set_working(self, is_working, text):
        self.status_label.configure(text=text)
        state = "disabled" if is_working else "normal"
        self.download_button.configure(state=state)
        self.clear_input_button.configure(state=state)
        self.task_menu.configure(state=state)
        self.settings_button.configure(state=state)
        self.mp3_button.configure(state=state)
        self.library_button.configure(state=state)
        self.local_transcript_button.configure(state=state)
        for button_name in (
            "download_shortcut_button",
            "fix_shortcut_button",
            "subtitle_shortcut_button",
            "ocr_shortcut_button",
            "transcript_shortcut_button",
            "compress_video_button",
            "action_enhance_video_button",
            "hero_enhance_video_button",
            "full_shortcut_button",
            "choose_bg_button",
            "clear_bg_button",
            "open_settings_card_button",
            "hero_choose_bg_button",
            "hero_clear_bg_button",
            "action_check_tools_button",
        ):
            button = getattr(self, button_name, None)
            if button:
                button.configure(state=state)
        self.copy_log_button.configure(state="normal")
        self.check_tools_button.configure(state=state)
        self.refresh_cookie_button.configure(state=state)
        self.open_platform_button.configure(state="normal")
        self.detail_log_button.configure(state="normal")

    def _prepare_folders(self):
        root = self._download_root() if hasattr(self, "settings") else CREATOR_DIR
        for item in DOWNLOAD_PLATFORMS.values():
            platform_root = root / item["folder_name"]
            for folder_name in (VIDEO_DIR_NAME, FIXED_DIR_NAME, SUBTITLE_DIR_NAME, OCR_DIR_NAME, TRANSCRIPT_DIR_NAME):
                (platform_root / folder_name).mkdir(parents=True, exist_ok=True)
            if item["name"] in ("抖音", "小红书"):
                (platform_root / NOTE_DIR_NAME).mkdir(parents=True, exist_ok=True)
            if item["name"] == "微博":
                (platform_root / "Audio").mkdir(parents=True, exist_ok=True)

        (root / UNKNOWN_PLATFORM["folder_name"]).mkdir(parents=True, exist_ok=True)
        (root / "Audio").mkdir(parents=True, exist_ok=True)
        (root / COMPRESSED_DIR_NAME).mkdir(parents=True, exist_ok=True)
        (root / ENHANCED_DIR_NAME).mkdir(parents=True, exist_ok=True)

    def _check_required_tools_on_startup(self, show_popup=True):
        checks = []
        missing = []
        self._write_log(f"ACAN Studio 版本：{__version__}")

        def add_check(ok, label, warn_message=None):
            checks.append(f"{'✓' if ok else '⚠'} {label}")
            if not ok and warn_message:
                missing.append(warn_message)

        add_check(bool(self._find_tool("yt-dlp")), "yt-dlp", "yt-dlp 未检测到")
        add_check(bool(self._find_tool("deno")), "YouTube JavaScript 运行时 Deno", "Deno 未检测到（YouTube 下载需要）")
        add_check(bool(self._find_tool("ffmpeg")), "ffmpeg", "ffmpeg 未检测到")
        ocr_engine = self._detect_ocr_engine()
        add_check(bool(ocr_engine), f"OCR 引擎 {ocr_engine['name']}" if ocr_engine else "OCR 引擎未安装", "OCR 引擎未安装")
        transcript_engine = self._detect_transcript_engine()
        add_check(bool(transcript_engine), f"语音识别 {transcript_engine['name']}" if transcript_engine else "语音识别未安装", "语音识别未安装")
        add_check(True, "Python")
        try:
            certificate_count = create_https_context().cert_store_stats()["x509_ca"]
            add_check(certificate_count > 0, f"HTTPS 信任证书已加载（{certificate_count} 个根证书）", "HTTPS 信任证书未加载")
        except Exception as exc:
            add_check(False, "HTTPS 信任证书加载失败", "HTTPS 信任证书加载失败")
            self._write_log(f"HTTPS 证书检查：{exc}")

        try:
            self._download_root().mkdir(parents=True, exist_ok=True)
            add_check(True, "下载目录")
        except OSError:
            add_check(False, "下载目录", "下载目录无法创建或访问")

        cookie_source = self.settings.get("cookie_source", "不使用")
        browser_label = self.settings.get("browser", "自动")
        if cookie_source == "Cookies.txt":
            cookies_txt = self.settings.get("cookies_txt", "").strip()
            cookie_status = bool(cookies_txt and Path(cookies_txt).expanduser().is_file())
            add_check(cookie_status, "Cookies.txt 可读取" if cookie_status else "Cookies.txt 未找到", "Cookies.txt 未找到")
        elif cookie_source == "浏览器" and self.settings.get("use_browser_cookie", False):
            display_name = "Chrome" if browser_label == "自动" else browser_label
            browser_ok = self._browser_available(browser_label)
            add_check(
                browser_ok,
                f"{display_name} Cookie 已启用（下载时验证）" if browser_ok else f"{display_name} 未检测到",
                f"{display_name} 未检测到",
            )
        else:
            add_check(True, "Cookie 未启用（可选）")

        env_text = "环境检查\n" + "    ".join(checks)
        self.env_label.configure(text=env_text)
        for line in checks:
            self._write_log(f"环境检查：{line}")

        if missing and show_popup:
            message = "环境检查发现问题：\n" + "\n".join(f"• {item}" for item in missing)
            messagebox.showwarning("提示", message)

    def _browser_available(self, browser_label):
        candidates = {
            "自动": ["/Applications/Google Chrome.app"],
            "Chrome": ["/Applications/Google Chrome.app"],
            "Safari": ["/Applications/Safari.app", "/System/Applications/Safari.app"],
            "Edge": ["/Applications/Microsoft Edge.app"],
            "Firefox": ["/Applications/Firefox.app"],
        }
        return any(Path(path).exists() for path in candidates.get(browser_label, []))

    def _cookie_status_ok(self):
        cookie_source = self.settings.get("cookie_source", "不使用")
        cookies_txt = self.settings.get("cookies_txt", "").strip()
        if cookie_source == "Cookies.txt":
            return bool(cookies_txt and Path(cookies_txt).expanduser().is_file())

        if cookie_source != "浏览器" or not self.settings.get("use_browser_cookie", False):
            return False

        return any(path.exists() and os.access(path, os.R_OK) for path in self._chrome_cookie_paths())

    @staticmethod
    def _chrome_cookie_paths():
        return [
            Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies",
            Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
            Path.home() / "Library/Application Support/Google/Chrome/Profile 2/Cookies",
        ]

    @staticmethod
    def _embedded_resource_roots():
        roots = []

        def add(path):
            if not path:
                return
            try:
                resolved = Path(path).expanduser().resolve()
            except Exception:
                return
            if resolved not in roots:
                roots.append(resolved)

        add(os.environ.get("ACAN_STUDIO_EMBEDDED_TOOLS_DIR"))
        add(getattr(sys, "_MEIPASS", None))

        if getattr(sys, "frozen", False):
            try:
                executable = Path(sys.executable).resolve()
                add(executable.parent.parent / "Resources")
                add(executable.parent)
            except Exception:
                pass

        return roots

    @classmethod
    def _bundled_tool_path(cls, tool_name):
        for root in cls._embedded_resource_roots():
            for candidate in (
                root / EMBEDDED_TOOL_DIR_NAME / tool_name,
                root / tool_name,
            ):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
        return None

    @classmethod
    def _bundled_tessdata_dir(cls):
        for root in cls._embedded_resource_roots():
            candidate = root / EMBEDDED_TESSDATA_DIR_NAME
            if candidate.is_dir():
                return candidate
        return None

    @classmethod
    def _bundled_whisper_model_dir(cls):
        for root in cls._embedded_resource_roots():
            candidate = root / EMBEDDED_MODEL_DIR_NAME / FASTER_WHISPER_MODEL_DIR_NAME
            if candidate.is_dir() and (candidate / "model.bin").is_file():
                return candidate
        return None

    @classmethod
    def _configure_embedded_environment(cls):
        tool_dirs = []
        for root in cls._embedded_resource_roots():
            tool_dir = root / EMBEDDED_TOOL_DIR_NAME
            if tool_dir.is_dir():
                tool_dirs.append(str(tool_dir))

        if tool_dirs:
            current_path = os.environ.get("PATH", "")
            os.environ["PATH"] = os.pathsep.join([*tool_dirs, current_path])

        tessdata_dir = cls._bundled_tessdata_dir()
        if tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)

    def _find_tool(self, tool_name):
        bundled_path = self._bundled_tool_path(tool_name)
        if bundled_path:
            return bundled_path

        path = shutil.which(tool_name)
        if path:
            return path

        for folder in COMMON_TOOL_DIRS:
            candidate = Path(folder) / tool_name
            if candidate.exists() and os.access(candidate, os.X_OK):
                return str(candidate)

        return None

    def _detect_ocr_engine(self):
        vision_path = self._find_tool("acan-vision-ocr") if sys.platform == "darwin" else None
        if vision_path:
            return {"kind": "vision", "name": "macOS Vision（内置）", "path": vision_path}

        if self._paddleocr_available():
            return {"kind": "paddle", "name": "PaddleOCR", "path": ""}

        tesseract_path = self._find_tool("tesseract")
        if tesseract_path and self._tesseract_python_available():
            return {"kind": "tesseract", "name": "Tesseract", "path": tesseract_path}

        return None

    @staticmethod
    def _candidate_project_dirs():
        candidates = []

        def add(path):
            try:
                path = Path(path).resolve()
            except Exception:
                return
            if path not in candidates:
                candidates.append(path)

        env_project = os.environ.get("ACAN_STUDIO_PROJECT_DIR")
        if env_project:
            add(env_project)

        add(Path.cwd())
        try:
            add(Path(__file__).resolve().parent)
        except Exception:
            pass

        for base in list(candidates):
            for parent in [base, *base.parents]:
                add(parent)
                if parent.name == "dist":
                    add(parent.parent)

        return candidates

    @staticmethod
    def _project_venv_python():
        for project_dir in ACANCreatorApp._candidate_project_dirs():
            python_path = project_dir / ".venv" / "bin" / "python"
            if python_path.exists():
                return python_path
        return None

    @staticmethod
    def _project_whisper_cli():
        for project_dir in ACANCreatorApp._candidate_project_dirs():
            whisper_path = project_dir / ".venv" / "bin" / "whisper"
            if whisper_path.exists():
                return whisper_path
        return None

    @staticmethod
    def _detect_transcript_engine():
        if ACANCreatorApp._faster_whisper_available():
            bundled = ACANCreatorApp._bundled_whisper_model_dir()
            name = "faster-whisper（内置模型）" if bundled else "faster-whisper"
            return {"kind": "faster-whisper", "name": name}

        whisper_cli = ACANCreatorApp._project_whisper_cli() or shutil.which("whisper")
        if whisper_cli:
            return {"kind": "whisper-cli", "name": "Whisper", "path": str(whisper_cli)}

        if ACANCreatorApp._whisper_available():
            return {"kind": "whisper", "name": "Whisper"}
        return None

    def _log_ocr_engine_status(self):
        self._write_log("OCR 引擎：")
        vision_path = self._find_tool("acan-vision-ocr") if sys.platform == "darwin" else None
        if vision_path:
            self._write_log(f"✓ macOS Vision（内置：{vision_path}）")
            return

        if self._paddleocr_available():
            self._write_log("✓ PaddleOCR")
            return

        tesseract_path = self._find_tool("tesseract")
        if tesseract_path and self._tesseract_python_available():
            self._write_log(f"✓ Tesseract（{tesseract_path}）")
            return

        self._write_log("✗ 未安装")
        if tesseract_path and not self._tesseract_python_available():
            self._write_log("Tesseract 已安装，但缺少 Python 依赖 pytesseract / Pillow。")

    def _log_transcript_engine_status(self):
        self._write_log("语音识别引擎：")
        transcript_engine = self._detect_transcript_engine()
        if transcript_engine:
            self._write_log(f"✓ {transcript_engine['name']}")
            return
        self._write_log("✗ 未安装")
        self._write_log("中文解决建议：需要安装语音识别引擎 Whisper，才能把采访/音频内容转成文字。")

    @staticmethod
    def _paddleocr_available():
        try:
            import paddleocr  # noqa: F401
        except Exception:
            return False
        return True

    @staticmethod
    def _tesseract_python_available():
        try:
            import PIL  # noqa: F401
            import pytesseract  # noqa: F401
        except Exception:
            return False
        return True

    @staticmethod
    def _faster_whisper_available():
        try:
            import faster_whisper  # noqa: F401
            return True
        except Exception:
            pass

        project_python = ACANCreatorApp._project_venv_python()
        if project_python:
            try:
                result = subprocess.run(
                    [str(project_python), "-c", "import faster_whisper"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return result.returncode == 0
            except Exception:
                pass
        return False

    @staticmethod
    def _whisper_available():
        if ACANCreatorApp._project_whisper_cli() or shutil.which("whisper"):
            return True

        try:
            import whisper  # noqa: F401
            return True
        except Exception:
            pass

        project_python = ACANCreatorApp._project_venv_python()
        if project_python:
            try:
                result = subprocess.run(
                    [str(project_python), "-c", "import whisper"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return result.returncode == 0
            except Exception:
                pass
        return False

    @staticmethod
    def _python_ocr_packages_available():
        return ACANCreatorApp._paddleocr_available() or ACANCreatorApp._tesseract_python_available()

    def _command_environment(self):
        env = os.environ.copy()
        current_path = env.get("PATH", "")
        tool_dirs = []
        for root in self._embedded_resource_roots():
            tool_dir = root / EMBEDDED_TOOL_DIR_NAME
            if tool_dir.is_dir():
                tool_dirs.append(str(tool_dir))
        env["PATH"] = os.pathsep.join([*tool_dirs, *COMMON_TOOL_DIRS, current_path])

        tessdata_dir = self._bundled_tessdata_dir()
        if tessdata_dir:
            env["TESSDATA_PREFIX"] = str(tessdata_dir)
        return env

    def _open_finder(self, path):
        try:
            target = Path(path)
            if target.is_file():
                subprocess.run(["open", "-R", str(target)], check=False)
            else:
                subprocess.run(["open", str(target)], check=False)
        except Exception as exc:
            self._write_log(f"打开 Finder 失败：{exc}")

    def _latest_file_since(self, folder, started_at):
        if not folder:
            return None

        folder = Path(folder)
        if not folder.exists():
            return None

        video_suffixes = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
        ignored_suffixes = {".part", ".ytdl", ".tmp", ".ds_store"}
        recent_candidates = []

        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in ignored_suffixes:
                continue
            if suffix not in video_suffixes:
                continue

            try:
                modified_at = path.stat().st_mtime
            except OSError:
                continue

            if modified_at >= started_at - 3:
                recent_candidates.append((modified_at, path))

        if recent_candidates:
            recent_candidates.sort(reverse=True)
            return recent_candidates[0][1]

        return None

    @staticmethod
    def _fixed_video_path(input_path, fixed_dir=None):
        input_path = Path(input_path)
        output_dir = Path(fixed_dir) if fixed_dir else input_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_fixed.mp4"
        index = 2

        while output_path.exists():
            output_path = output_dir / f"{input_path.stem}_fixed {index}.mp4"
            index += 1

        return output_path

    @staticmethod
    def _unique_transcript_path(transcript_dir, stem, suffix):
        safe_stem = stem.strip() or "transcript"
        output_path = Path(transcript_dir) / f"{safe_stem}_transcript{suffix}"
        index = 2

        while output_path.exists():
            output_path = Path(transcript_dir) / f"{safe_stem}_transcript {index}{suffix}"
            index += 1

        return output_path

    def _unique_audio_path(self, stem, suffix=".mp3"):
        safe_stem = stem.strip() or "音频"
        normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        audio_dir = self._download_root() / "Audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_path = audio_dir / f"{safe_stem}{normalized_suffix}"
        index = 2

        while output_path.exists():
            output_path = audio_dir / f"{safe_stem} {index}{normalized_suffix}"
            index += 1

        return output_path

    @staticmethod
    def _unique_compressed_path(compressed_dir, stem, target_size_mb=None):
        safe_stem = stem.strip() or "video"
        compressed_dir = Path(compressed_dir)
        compressed_dir.mkdir(parents=True, exist_ok=True)
        if target_size_mb:
            target_label = f"{int(float(target_size_mb))}MB" if float(target_size_mb).is_integer() else f"{target_size_mb:g}MB"
            output_path = compressed_dir / f"{safe_stem}_compressed_{target_label}.mp4"
            index_template = f"{safe_stem}_compressed_{target_label}_{{index}}.mp4"
        else:
            output_path = compressed_dir / f"{safe_stem}_compressed.mp4"
            index_template = f"{safe_stem}_compressed_{{index}}.mp4"
        index = 2

        while output_path.exists():
            output_path = compressed_dir / index_template.format(index=index)
            index += 1

        return output_path

    @staticmethod
    def _unique_enhanced_path(enhanced_dir, stem):
        safe_stem = stem.strip() or "video"
        enhanced_dir = Path(enhanced_dir)
        enhanced_dir.mkdir(parents=True, exist_ok=True)
        output_path = enhanced_dir / f"{safe_stem}_enhanced_4k.mp4"
        index = 2

        while output_path.exists():
            output_path = enhanced_dir / f"{safe_stem}_enhanced_4k_{index}.mp4"
            index += 1

        return output_path


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-https":
        from urllib.parse import urlsplit
        for check_url in sys.argv[2:]:
            if urlsplit(check_url).scheme != "https":
                raise SystemExit("--check-https 只支持 HTTPS 链接")
            with create_https_opener().open(check_url, timeout=15) as response:
                final_url = urlsplit(response.geturl())
                print(json.dumps({"version": __version__, "status": response.status,
                                  "url": final_url.scheme + "://" + final_url.netloc + final_url.path,
                                  "verified": True}, ensure_ascii=False))
        raise SystemExit(0)
    app = ACANCreatorApp()
    app.mainloop()
