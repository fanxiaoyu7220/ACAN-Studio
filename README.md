# ACAN Studio

> Open-source desktop media workspace for video creators.

ACAN Studio 是一个给视频创作者使用的 macOS 图形界面素材工作台，当前版本线为 **1.3.x**。它使用 Python 3 + CustomTkinter，后端调用 yt-dlp、FFmpeg 和可选的 OCR/Whisper 组件；既可以直接运行源码，也可以用 PyInstaller 打包成 `.app`。

项目当前处于持续开发阶段：下载、转码、音频格式转换、字幕、OCR、音频转文字和素材整理已经可用，1.3.x 正在继续改善创作者工作流。

English: [README.en.md](README.en.md)

文档入口：[贡献指南](CONTRIBUTING.md) · [变更记录](CHANGELOG.md) · [路线图](ROADMAP.md) · [安全说明](SECURITY.md)

这是一个可独立运行的开源项目。仓库只包含源码、构建脚本和文档，不包含个人素材、浏览器 Cookie、下载结果或本地虚拟环境。

## 网页测试版

为了让 Windows 用户无需安装即可更快体验，项目新增了独立的网页测试版。第一阶段支持公开视频链接、实时进度和结果下载，不读取浏览器 Cookie，也不处理会员、付费或 DRM 内容。网页端代码、Docker 部署方式和安全限制见 [web/README.md](web/README.md)。它与 macOS 桌面版相互独立，不会影响现有 DMG 构建。

## 开源与安全说明

- 源码以 MIT License 发布，详见 [LICENSE](LICENSE)。
- Chrome Cookie 和 `Cookies.txt` 仅在用户于设置中主动选择后使用，默认不读取浏览器 Cookie。
- 不要把 `Cookies.txt`、应用设置、日志、下载视频、字幕或 OCR/转写结果提交到仓库。
- 下载、转码、字幕提取和内容保存请遵守所在平台的服务条款、版权规定和内容发布者的授权范围。
- ACAN Studio 不绕过 DRM、付费墙或平台访问控制；项目作者不对下载内容的合法性负责。

## 功能

- 下载视频：粘贴链接或整段分享文案后，自动识别第一个 `http://` 或 `https://` 链接
- 手机分享文案预处理：自动提取链接，并解析 `v.douyin.com`、`xhslink.com`、`b23.tv`、`m.weibo.cn`、`youtu.be`
- 平台识别：抖音、小红书、微博、YouTube、B站，其他平台保存到 Other
- 内容类型判断：视频、图文/笔记、直播、合集、用户主页、未知
- 抖音/小红书短链：下载前会先解析跳转；图文/笔记会保存到 Note 并提示使用图文提取模式
- Cookie 管理：支持用户主动选择 Chrome Cookie 或 `Cookies.txt`，默认不读取 Cookie，失败时给中文登录建议
- 下载并修复：下载后自动用 `ffmpeg` 转成 H.264 视频编码 + AAC 音频编码的 MP4，文件名带 `_fixed`
- YouTube 下载后会自动生成剪映兼容 `_fixed.mp4`
- YouTube 网络中断时会自动使用分块断点续传、小分块续传和系统 `curl` 备用传输，并继承 macOS 代理设置
- 提取字幕：只提取视频已有官方字幕/自动字幕，支持 `zh-Hans`、`zh-CN`、`zh`、`en`，输出 `.srt` 和 `.txt`
- 画面文字 OCR：每隔 2 秒抽取一帧，用 OCR 识别画面上出现的文字，去重后保存为 `video_ocr_text.txt`
- 音频转文字：支持本地视频或已下载视频，先用 ffmpeg 提取 16kHz 单声道 WAV，再用 Whisper / faster-whisper 识别采访或语音内容，输出 `_transcript.txt` 和 `_transcript.srt`
- 一键完整流程：下载 + 修复 + 字幕 + OCR + 音频转文字
- 下载引擎架构：YouTube / 微博 / 抖音 / 小红书 / B站 均通过 Downloader Engine 选择下载方案，目前 Engine A 为 yt-dlp，备用解析器和浏览器辅助模式已预留接口
- 后台工具检测：检查 yt-dlp、ffmpeg、Chrome Cookie、OCR 引擎、Whisper / faster-whisper，并在日志中显示版本和状态
- 依赖安装向导：首次启动检测 OCR / Whisper，缺少时可一键安装
- 下载前会在日志中打印原始输入、最终解析 URL 和识别平台
- 自动识别平台：B站、小红书、微博、YouTube、抖音
- 抖音下载：先直接下载；仅在用户启用 Cookie 后，失败时才会使用 Cookie 重试
- 下载完成后自动打开保存目录，并尽量高亮刚下载的文件
- 下载时显示进度、速度和预计剩余时间
- 设置页：可设置下载目录、浏览器 Cookie、导入 Cookies.txt
- 启动时显示环境检查：yt-dlp、ffmpeg、OCR 引擎、Python、下载目录、浏览器、Cookie 状态
- 提取MP3：选择本地视频文件，后台调用 `ffmpeg`
- MP3 转 WAV：选择本地 MP3，转换为兼容性良好的 16-bit PCM WAV，并保留原采样率和声道
- 打开素材库：一键打开 `~/Movies/Creator/`
- 日志窗口：显示执行状态、错误信息和完成路径，可一键复制日志
- 可一键复制下载命令，方便在终端中调试

## 默认保存位置

```text
Creator/
  YouTube/
    Video/
    Fixed/
    Subtitles/
    OCR_Text/
    Transcript/
  Douyin/
    Video/
    Note/
    Fixed/
    Subtitles/
    OCR_Text/
    Transcript/
  Xiaohongshu/
    Video/
    Note/
    Fixed/
    Subtitles/
    OCR_Text/
    Transcript/
  Weibo/
    Video/
    Audio/
    Fixed/
    Subtitles/
    OCR_Text/
    Transcript/
  Bilibili/
    Video/
    Fixed/
    Subtitles/
    OCR_Text/
    Transcript/
  Other/
```

- B站视频：`~/Movies/Creator/Bilibili/Video/`
- YouTube视频：`~/Movies/Creator/YouTube/Video/`
- 抖音视频：`~/Movies/Creator/Douyin/Video/`
- 抖音图文/笔记链接：`~/Movies/Creator/Douyin/Note/`
- 小红书视频：`~/Movies/Creator/Xiaohongshu/Video/`
- 小红书图文/笔记链接：`~/Movies/Creator/Xiaohongshu/Note/`
- 剪映兼容版：各平台目录下的 `Fixed/`
- 字幕：各平台目录下的 `Subtitles/`
- OCR文本：各平台目录下的 `OCR_Text/video_ocr_text.txt`
- 音频转文字：各平台目录下的 `Transcript/`
- 其他平台：`~/Movies/Creator/Other/`
- MP3/WAV 音频：`~/Movies/Creator/Audio/`
- 素材库：`~/Movies/Creator/`

## 需要提前安装

源码直接运行时，后台需要这些工具：

- `yt-dlp`
- `deno`（YouTube 新版播放器的 JavaScript 挑战解析）
- `ffmpeg`
- `tesseract`（用于画面文字 OCR，可在应用里点击“立即安装 OCR”自动安装）
- `faster-whisper` 或 `openai-whisper`（用于音频转文字，可选安装）

如果没有安装，可以使用 Homebrew 安装：

```bash
brew install yt-dlp deno ffmpeg tesseract
```

使用已经构建好的兼容版 DMG 时，`yt-dlp`、`yt-dlp-ejs`、Deno、`ffmpeg`、`ffprobe`、macOS 原生 Vision OCR、`faster-whisper` 和 base 多语言模型会随应用一起提供，不需要在朋友的 Mac 上安装 Homebrew，也不需要首次使用时另行下载语音模型。

首次启动时，如果检测到 OCR 或 Whisper 缺失，会显示安装向导。点击“一键安装”会后台执行：

```bash
brew install tesseract
pip install faster-whisper
```

OCR 引擎优先级：

1. 如果已经安装 PaddleOCR，ACAN Studio 会优先使用 PaddleOCR。
2. 如果没有 PaddleOCR，会自动降级使用 Tesseract。
3. 如果两个 OCR 引擎都没有安装，点击“提取画面文字”时会弹出中文提示，并提供“立即安装 OCR”按钮，后台自动执行 `brew install tesseract`。

可选：如果你以后想使用 PaddleOCR，可以自行安装 PaddleOCR 插件环境；ACAN Studio 已预留自动识别接口。

音频转文字需要 Whisper 引擎。任选一种安装：

```bash
pip install faster-whisper
```

或：

```bash
pip install openai-whisper
```

如果没有安装 Whisper / faster-whisper，点击“音频转文字”时会提示：

```text
需要安装语音识别引擎 Whisper，才能把采访/音频内容转成文字。
```

## 安装依赖

进入项目目录：

```bash
cd path/to/repository
```

建议先创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 运行

```bash
python3 main.py
```

## 打包成 .app

先安装依赖，然后运行：

```bash
chmod +x build_app.sh
./build_app.sh
```

打包完成后，应用会出现在：

```text
dist/ACAN Studio.app
```

可以把这个 `.app` 拖到“应用程序”文件夹中使用。
如果项目目录下存在 `icon.icns`，打包时会自动使用它作为应用图标；没有则使用默认图标。

## 生成可下载的 DMG

发布版分别为 Apple Silicon 和 Intel Mac 构建，支持 macOS 12 及以上版本。在项目目录运行：

```bash
chmod +x build_macos_compat_dmg.sh
./build_macos_compat_dmg.sh arm64
./build_macos_compat_dmg.sh x86_64
```

完成后会同时保留两个安装包：

```text
dist/ACAN-Studio-1.3.0-arm64.dmg
dist/ACAN-Studio-1.3.0-x86_64.dmg
```

M1、M2、M3、M4、M5 等 Apple 芯片 Mac 下载 `arm64` 版；使用 Intel 处理器的 Mac 下载 `x86_64` 版。打开 DMG 后，把 `ACAN Studio.app` 拖到 `Applications` 文件夹即可。

当前 DMG 会把下载、转码、OCR 和语音识别所需的后台工具及第三方许可说明一起打进应用，并执行本地完整性签名。它仍是测试版，尚未使用 Apple Developer ID 签名和公证；朋友第一次打开时，如果 macOS 提示无法验证开发者，可以右键点击应用，选择“打开”后再确认。

兼容版构建需要 Xcode Command Line Tools 和网络连接。Intel 版在 Apple Silicon Mac 上构建时，还需要苹果官方 Rosetta 2：

```bash
xcode-select --install
softwareupdate --install-rosetta --agree-to-license
```

## 说明

- 所有下载、转码命令都在后台执行，不会打开终端窗口。
- “下载并修复”会生成适合剪映导入的 `_fixed.mp4` 文件。
- YouTube 即使选择“下载视频”，也会额外生成一份 `_fixed.mp4`，避免剪映导入黑屏或无画面。
- 字幕、OCR、音频转文字是三个不同功能：字幕只下载平台已有字幕；OCR 识别画面上的文字；音频转文字识别视频里说的话。
- OCR 优先使用 PaddleOCR，没有则自动使用 Tesseract；如果都没有安装，应用会弹出中文提示并提供“立即安装 OCR”按钮，不会闪退。
- 如果视频没有字幕，应用会提示使用“音频转文字”识别语音内容。
- 默认不会读取浏览器 Cookie。需要登录的平台，请在“设置”中主动选择“浏览器”，或手动导入 `Cookies.txt`。
- 如果提示 Cookie 或 JSON 解析问题，请打开对应平台的网页版并确认已登录，必要时运行 `yt-dlp -U` 更新下载器。
- 芒果TV会员内容会使用当前网页播放器所需的设备与会话参数读取已登录账号有权限播放的清晰度；如果平台仍只返回约5分钟试看流，ACAN Studio 会比较页面标称时长与实际文件时长，保留并标记为 `INCOMPLETE`，不会误报为完整下载。此功能不会绕过会员、付费或版权权限。
- 芒果TV标记为“SVIP限时抢先看”的内容会在下载前检查当前账号权限；权限不足时直接停止并提示，不再下载2分钟试看文件。
- 下载器发现目标视频已经存在时，会根据 yt-dlp 返回的精确文件路径校验同一个视频，不会再回退误选目录里的其他旧视频。
- 如果抖音出现 `Fresh cookies are needed` 或 `Failed to parse JSON`，说明链接已成功识别，但当前 yt-dlp 可能无法解析抖音接口数据；请稍后更新 yt-dlp 后重试，或使用后续备用下载方案。
- 小红书如果需要登录，请在 Mac 的 Chrome 中登录小红书网页版；手机 App 登录状态不能被电脑读取。
- 抖音精选页链接如 `https://www.douyin.com/jingxuan?modal_id=...` 会直接提示用户进入具体视频页面后使用“分享 → 复制链接”，不会继续交给 yt-dlp。
- 可以直接粘贴带标题、换行和分享文案的内容，程序会自动提取第一个有效视频链接。
- 如果任务失败，弹窗会显示具体错误原因，完整输出会保留在应用底部的日志窗口。
- 常见错误：
  - Cookie 失效：在 Mac 的 Chrome 登录对应平台网页版，浏览几个视频后重试。
  - 平台不支持：打开最终链接确认是否是视频页，或改用录屏/截图整理模式。
  - 无字幕：使用【音频转文字】识别语音内容。
  - OCR 未安装：使用安装向导安装 Tesseract。
  - Whisper 未安装：使用安装向导安装 faster-whisper。
- 预留扩展方向：AI字幕、AI提取金句、AI采访整理、AI脚本生成、AI封面生成。
