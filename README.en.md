# ACAN Studio

> Open-source desktop media workspace for video creators.

ACAN Studio is a macOS-first desktop app for creators who need one place to download, repair, convert, transcribe, and organize media. It combines a CustomTkinter GUI with `yt-dlp`, FFmpeg, and optional OCR/Whisper components.

The project is in active development on the 1.3.x line. The source app is usable today; the current work focuses on reliable creator workflows, predictable releases, and contributor-friendly maintenance.

Chinese documentation: [README.md](README.md)

## What it does

- Download media from supported public URLs and pasted sharing text
- Detect common platforms and content types before downloading
- Repair downloaded files into broadly compatible H.264/AAC MP4 files
- Convert local video/audio files, extract MP3 audio, and convert MP3 to 16-bit PCM WAV
- Extract available subtitles as SRT and TXT
- Run optional OCR on video frames
- Transcribe local media with Whisper/faster-whisper when installed
- Organize outputs by platform and media type
- Show progress, logs, tool status, and actionable failure suggestions

## Privacy and responsible use

- Browser cookies are never read by default.
- Chrome cookies or an imported `Cookies.txt` file are used only after the user explicitly enables them.
- Do not commit cookies, credentials, personal media, logs, or generated outputs.
- Use the app only for media you are authorized to access, save, and process.
- ACAN Studio does not bypass DRM, paywalls, or platform access controls.

## Download

Visit the [latest GitHub release](https://github.com/fanxiaoyu7220/ACAN-Studio/releases/latest) for packaged macOS builds when available. The project currently targets macOS and is being prepared for repeatable arm64/x86_64 release builds.

## Run from source

The GUI requires Python 3, CustomTkinter, Pillow, and the optional tools used by the features you enable. FFmpeg and yt-dlp are recommended for the core media workflow.

```bash
git clone https://github.com/fanxiaoyu7220/ACAN-Studio.git
cd ACAN-Studio
python3 -m pip install -r requirements.txt
python3 main.py
```

For packaged macOS builds, see:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [ROADMAP.md](ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)

## Development

The dependency-light core is covered by the standard-library test suite:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q main.py ui_v2.py acan_studio tests
```

Pull requests should keep changes focused, add regression coverage where practical, and update the changelog for user-visible behavior. See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete workflow.

## License

ACAN Studio is released under the [MIT License](LICENSE).
