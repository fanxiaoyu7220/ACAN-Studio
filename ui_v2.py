import tkinter as tk

import customtkinter as ctk


def build_ui_v2(app, app_name, video_task_options):
    """ACAN Studio Lite UI.

    Stable, plain interface: no background images, no Hero picture layer,
    no experimental V3 overlays. The goal is speed and reliability.
    """
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    app.content_frame = ctk.CTkFrame(app, fg_color="#090B10")
    app.content_frame.grid(row=0, column=0, sticky="nsew")
    app.content_frame.grid_columnconfigure(0, weight=1)
    app.content_frame.grid_rowconfigure(0, weight=1)

    app.scroll_canvas = tk.Canvas(
        app.content_frame,
        highlightthickness=0,
        borderwidth=0,
        bg="#090B10",
    )
    app.scroll_canvas.grid(row=0, column=0, sticky="nsew")

    app.scrollbar = ctk.CTkScrollbar(
        app.content_frame,
        orientation="vertical",
        command=app._scroll_canvas_yview,
    )
    app.scrollbar.grid(row=0, column=1, sticky="ns")
    app.scroll_canvas.configure(yscrollcommand=app.scrollbar.set)

    app.scrollable_frame = ctk.CTkFrame(app.scroll_canvas, fg_color="#090B10")
    app.main_content_frame = app.scrollable_frame
    app.content_window = app.scroll_canvas.create_window((0, 0), window=app.scrollable_frame, anchor="nw")
    app.main_content_frame.grid_columnconfigure(0, weight=1)
    app.main_content_frame.grid_rowconfigure(1, weight=1)

    app.scroll_canvas.bind("<Configure>", app._on_scroll_canvas_configure)
    app.scrollable_frame.bind("<Configure>", app._on_scrollable_frame_configure)

    _build_hero(app, app_name)
    _build_body(app, video_task_options)
    app._bind_main_scroll_widgets()


def _build_hero(app, app_name):
    app.hero_frame = ctk.CTkFrame(
        app.main_content_frame,
        height=210,
        corner_radius=22,
        fg_color="#141824",
        border_width=1,
        border_color="#343B4E",
    )
    app.hero_frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
    app.hero_frame.grid_propagate(False)
    app.hero_frame.grid_columnconfigure(0, weight=1)

    app.hero_title_label = ctk.CTkLabel(
        app.hero_frame,
        text=app_name,
        font=ctk.CTkFont(size=34, weight="bold"),
        text_color="#FFFFFF",
        anchor="w",
    )
    app.hero_title_label.grid(row=0, column=0, sticky="w", padx=24, pady=(34, 0))

    app.hero_subtitle_label = ctk.CTkLabel(
        app.hero_frame,
        text="视频创作者素材工作台",
        font=ctk.CTkFont(size=17, weight="bold"),
        text_color="#F3F4F8",
        anchor="w",
    )
    app.hero_subtitle_label.grid(row=1, column=0, sticky="w", padx=26, pady=(6, 0))

    app.hero_desc_label = ctk.CTkLabel(
        app.hero_frame,
        text="追星剪辑素材整理 / 下载 / OCR / Whisper / 剪映兼容",
        font=ctk.CTkFont(size=13),
        text_color="#D8DCE8",
        anchor="w",
    )
    app.hero_desc_label.grid(row=2, column=0, sticky="w", padx=26, pady=(8, 0))

    app.settings_button = _button(app.hero_frame, "设置", app.open_settings, width=92, height=32)
    app.settings_button.place(relx=1, x=-22, y=24, anchor="ne")

    app.hero_enhance_video_button = _button(
        app.hero_frame,
        "修复画质4K",
        app.enhance_video_4k,
        width=150,
        height=44,
    )
    app.hero_enhance_video_button.place(relx=1, x=-22, y=70, anchor="ne")

    app.status_label = ctk.CTkLabel(
        app.hero_frame,
        text="准备就绪",
        font=ctk.CTkFont(size=14),
        text_color="#F7F8FA",
        fg_color="#252833",
        corner_radius=12,
        padx=12,
        pady=4,
    )
    app.status_label.place(relx=1, x=-22, y=126, anchor="ne")

    app.hero_library_label = ctk.CTkLabel(
        app.hero_frame,
        text=f"素材库位置：{app._download_root()}",
        font=ctk.CTkFont(size=13),
        text_color="#F7F8FA",
        fg_color="#252833",
        corner_radius=12,
        padx=12,
        pady=4,
    )
    app.hero_library_label.place(x=22, rely=1, y=-22, anchor="sw")



def _build_body(app, video_task_options):
    app.body_frame = ctk.CTkFrame(app.main_content_frame, fg_color="transparent")
    app.body_frame.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 18))
    app.body_frame.grid_columnconfigure(0, weight=6, uniform="body")
    app.body_frame.grid_columnconfigure(1, weight=5, uniform="body")

    app.left_column = ctk.CTkFrame(app.body_frame, fg_color="transparent")
    app.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    app.left_column.grid_columnconfigure(0, weight=1)

    app.right_column = ctk.CTkFrame(app.body_frame, fg_color="transparent")
    app.right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    app.right_column.grid_columnconfigure(0, weight=1)
    app.right_column.grid_rowconfigure(0, weight=1)

    _build_link_card(app, video_task_options)
    _build_actions_card(app)
    _build_settings_card(app)
    _build_log_card(app)


def _build_link_card(app, video_task_options):
    app.main_frame = _card(app.left_column)
    app.main_frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
    app.main_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        app.main_frame,
        text="链接输入",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#F7F8FA",
        anchor="w",
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8))

    app.url_entry = ctk.CTkTextbox(
        app.main_frame,
        height=126,
        corner_radius=16,
        font=ctk.CTkFont(size=15),
        wrap="word",
        fg_color="#10131A",
        border_width=1,
        border_color="#343B4E",
        text_color="#F7F8FA",
    )
    app.url_entry.grid(row=1, column=0, sticky="ew", padx=(20, 12), pady=(0, 14))
    app.url_entry.bind("<KeyRelease>", app._update_platform_preview)

    app.download_button = _button(app.main_frame, "开始执行", app.download_video, width=144, height=52)
    app.download_button.grid(row=1, column=1, sticky="new", padx=(0, 20), pady=(0, 8))

    app.clear_input_button = _button(app.main_frame, "清空链接", app.clear_input, width=144, height=34)
    app.clear_input_button.grid(row=1, column=1, sticky="sew", padx=(0, 20), pady=(64, 14))

    app.platform_label = _muted_label(app.main_frame, "识别平台：等待粘贴链接")
    app.platform_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 6))

    app.content_type_label = _muted_label(app.main_frame, "内容类型：等待识别")
    app.content_type_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 14))

    app.task_frame = ctk.CTkFrame(app.main_frame, fg_color="transparent")
    app.task_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
    app.task_frame.grid_columnconfigure(1, weight=1)
    _muted_label(app.task_frame, "执行方式").grid(row=0, column=0, sticky="w", padx=(0, 12))
    app.task_menu = ctk.CTkOptionMenu(
        app.task_frame,
        values=video_task_options,
        variable=app.task_mode_var,
        height=36,
        width=230,
        fg_color="#252833",
        button_color="#303443",
        button_hover_color="#3A4052",
    )
    app.task_menu.grid(row=0, column=1, sticky="w")

    app.progress_frame = ctk.CTkFrame(app.main_frame, fg_color="transparent")
    app.progress_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
    app.progress_frame.grid_columnconfigure(0, weight=1)
    app.progress_bar = ctk.CTkProgressBar(app.progress_frame, height=8, corner_radius=8)
    app.progress_bar.grid(row=0, column=0, sticky="ew")
    app.progress_bar.set(0)
    app.progress_label = _muted_label(app.progress_frame, "下载进度：等待开始")
    app.progress_label.grid(row=1, column=0, sticky="w", pady=(6, 0))


def _build_actions_card(app):
    app.button_frame = _card(app.left_column)
    app.button_frame.grid(row=1, column=0, sticky="ew", pady=(0, 14))
    app.button_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="actions")

    ctk.CTkLabel(
        app.button_frame,
        text="功能按钮",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#F7F8FA",
        anchor="w",
    ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(18, 10))

    app.download_shortcut_button = _task_button(app, "下载视频", "下载视频")
    app.download_shortcut_button.grid(row=1, column=0, sticky="ew", padx=(20, 8), pady=7)
    app.fix_shortcut_button = _task_button(app, "修复剪映兼容 MP4", "下载并修复")
    app.fix_shortcut_button.grid(row=1, column=1, sticky="ew", padx=8, pady=7)
    app.subtitle_shortcut_button = _task_button(app, "提取字幕", "提取字幕")
    app.subtitle_shortcut_button.grid(row=1, column=2, sticky="ew", padx=(8, 20), pady=7)

    app.ocr_shortcut_button = _task_button(app, "画面文字 OCR", "画面文字 OCR")
    app.ocr_shortcut_button.grid(row=2, column=0, sticky="ew", padx=(20, 8), pady=7)
    app.transcript_shortcut_button = _task_button(app, "音频转文字", "音频转文字")
    app.transcript_shortcut_button.grid(row=2, column=1, sticky="ew", padx=8, pady=7)
    app.mp3_button = _button(app.button_frame, "提取 MP3", app.extract_mp3, height=46)
    app.mp3_button.grid(row=2, column=2, sticky="ew", padx=(8, 20), pady=7)

    app.mp3_to_wav_button = _button(app.button_frame, "MP3 转 WAV", app.convert_mp3_to_wav, height=46)
    app.mp3_to_wav_button.grid(row=3, column=0, sticky="ew", padx=(20, 8), pady=7)
    app.compress_video_button = _button(app.button_frame, "压缩视频", app.compress_video, height=46)
    app.compress_video_button.grid(row=3, column=1, sticky="ew", padx=8, pady=7)
    app.library_button = _button(app.button_frame, "打开素材库", app.open_library, height=46)
    app.library_button.grid(row=3, column=2, sticky="ew", padx=(8, 20), pady=7)
    app.action_check_tools_button = _button(app.button_frame, "环境检测", app.check_backend_tools, height=46)
    app.action_check_tools_button.grid(row=4, column=0, columnspan=3, sticky="ew", padx=20, pady=7)

    app.action_enhance_video_button = _button(app.button_frame, "修复画质4K\n选择本地视频，增强清晰度并导出", app.enhance_video_4k, height=58)
    app.action_enhance_video_button.grid(row=5, column=0, columnspan=3, sticky="ew", padx=20, pady=7)

    app.full_shortcut_button = _task_button(app, "下载 + 修复 + 字幕 + OCR + 音频转文字", "下载 + 修复 + 字幕 + OCR + 音频转文字")
    app.full_shortcut_button.grid(row=6, column=0, columnspan=3, sticky="ew", padx=20, pady=(8, 18))

    app.local_transcript_button = _button(app.button_frame, "选择本地视频音频转文字", app.transcribe_local_video, height=46)
    app.local_transcript_button.grid(row=7, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 20))


def _build_settings_card(app):
    app.settings_card = _card(app.left_column)
    app.settings_card.grid(row=2, column=0, sticky="ew")
    app.settings_card.grid_columnconfigure((0, 1, 2), weight=1)

    ctk.CTkLabel(
        app.settings_card,
        text="设置",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#F7F8FA",
        anchor="w",
    ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(18, 8))

    app.library_path_label = _muted_label(app.settings_card, f"素材库路径：{app._download_root()}")
    app.library_path_label.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 12))

    app.open_settings_card_button = _button(app.settings_card, "更多设置", app.open_settings, height=42)
    app.open_settings_card_button.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 18))

    app.env_frame = _panel(app.settings_card)
    app.env_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 20))
    app.env_frame.grid_columnconfigure(0, weight=1)
    app.env_label = _muted_label(app.env_frame, "环境检查：准备检测")
    app.env_label.grid(row=0, column=0, sticky="ew", padx=16, pady=12)


def _build_log_card(app):
    app.log_card = _card(app.right_column)
    app.log_card.grid(row=0, column=0, sticky="nsew")
    app.log_card.grid_columnconfigure(0, weight=1)
    app.log_card.grid_rowconfigure(1, weight=1)

    app.log_header = ctk.CTkFrame(app.log_card, fg_color="transparent")
    app.log_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
    app.log_header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        app.log_header,
        text="日志窗口",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#F7F8FA",
        anchor="w",
    ).grid(row=0, column=0, sticky="w")

    app.copy_log_button = _button(app.log_header, "复制日志", app.copy_logs, width=92, height=32)
    app.copy_log_button.grid(row=0, column=1, sticky="e")
    app.copy_command_button = _button(app.log_header, "复制命令", app.copy_command, width=92, height=32)
    app.copy_command_button.grid(row=0, column=2, sticky="e", padx=(8, 0))
    app.check_tools_button = _button(app.log_header, "环境检测", app.check_backend_tools, width=100, height=32)
    app.check_tools_button.grid(row=0, column=3, sticky="e", padx=(8, 0))

    app.log_tools_frame = ctk.CTkFrame(app.log_card, fg_color="transparent")
    app.log_tools_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
    app.log_tools_frame.grid_columnconfigure((0, 1, 2), weight=1)
    app.refresh_cookie_button = _button(app.log_tools_frame, "重新读取 Cookie", app.refresh_cookie_status, height=34)
    app.refresh_cookie_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    app.open_platform_button = _button(app.log_tools_frame, "打开平台官网", app.open_current_platform_site, height=34)
    app.open_platform_button.grid(row=0, column=1, sticky="ew", padx=8)
    app.detail_log_button = _button(app.log_tools_frame, "查看详细日志", app.show_detailed_logs, height=34)
    app.detail_log_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

    app.log_text = ctk.CTkTextbox(
        app.log_card,
        height=620,
        corner_radius=16,
        font=ctk.CTkFont(size=13),
        wrap="word",
        fg_color="#0D1017",
        border_width=1,
        border_color="#343B4E",
        text_color="#F7F8FA",
    )
    app.log_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))


def _task_button(app, title, mode):
    return _button(app.button_frame, title, lambda selected_mode=mode: _run_task_mode(app, selected_mode), height=46)


def _run_task_mode(app, mode):
    app.task_mode_var.set(mode)
    app.download_video()


def _button(parent, title, command, width=None, height=42):
    return ctk.CTkButton(
        parent,
        text=title,
        width=width or 120,
        height=height,
        corner_radius=14,
        fg_color="#252833",
        hover_color="#303443",
        border_width=1,
        border_color="#4B5264",
        text_color="#F7F8FA",
        command=command,
    )


def _card(parent):
    return ctk.CTkFrame(
        parent,
        corner_radius=22,
        fg_color="#171A22",
        border_width=1,
        border_color="#343B4E",
    )


def _panel(parent):
    return ctk.CTkFrame(
        parent,
        corner_radius=16,
        fg_color="#20242E",
        border_width=1,
        border_color="#3A4152",
    )


def _muted_label(parent, text):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=13),
        text_color="#AEB6C8",
        anchor="w",
        justify="left",
    )
