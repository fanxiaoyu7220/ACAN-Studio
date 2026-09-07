#!/bin/zsh
set -e

cd "$(dirname "$0")"

APP_NAME="ACAN Studio"
PYTHON_BIN="${ACAN_PYTHON_BIN:-.venv/bin/python}"
REQUIREMENTS_FILE="${ACAN_REQUIREMENTS_FILE:-requirements.txt}"
APP_BUNDLE="dist/$APP_NAME.app"
APP_EXECUTABLE="$APP_BUNDLE/Contents/MacOS/$APP_NAME"
APPLICATIONS_APP="/Applications/$APP_NAME.app"
BUNDLE_ID="com.acan.studio"
ICON_PATH="icon.icns"
MACOS_RUNTIME_HOOK="$PWD/packaging/runtime_hook_macos_version.py"
PYINSTALLER_RUNNER="$PWD/packaging/run_pyinstaller.py"
WHISPER_MODEL_DIR="$PWD/.pyinstaller-cache/models/faster-whisper-base"
TARGET_ARCH="${ACAN_TARGET_ARCH:-}"
VERSION_FILE="$PWD/VERSION"
if [ -n "${ACAN_VERSION:-}" ]; then
  VERSION="$ACAN_VERSION"
else
  VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
fi
export MACOSX_DEPLOYMENT_TARGET="${ACAN_MACOSX_DEPLOYMENT_TARGET:-11.0}"
export PYINSTALLER_CONFIG_DIR="${ACAN_PYINSTALLER_CONFIG_DIR:-$PWD/.pyinstaller-cache}"

find_tool() {
  command -v "$1" 2>/dev/null || true
}

YTDLP_PATH="$(find_tool yt-dlp)"
FFMPEG_PATH="$(find_tool ffmpeg)"
TESSERACT_PATH="$(find_tool tesseract)"

echo "正在准备打包环境..."
if [ ! -x "$PYTHON_BIN" ]; then
  if [ -n "${ACAN_PYTHON_BIN:-}" ]; then
    echo "打包失败：指定的 Python 不可执行：$PYTHON_BIN"
    exit 1
  fi
  python3 -m venv .venv
fi

echo "正在安装 Python 依赖..."
"$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$REQUIREMENTS_FILE"

echo "正在检查后台工具..."
if [ -x "$YTDLP_PATH" ]; then
  echo "已找到 yt-dlp：$YTDLP_PATH"
else
  echo "提示：未找到 yt-dlp。应用仍会打包，但下载时会用中文提示用户安装。"
fi

if [ -x "$FFMPEG_PATH" ]; then
  echo "已找到 ffmpeg：$FFMPEG_PATH"
else
  echo "提示：未找到 ffmpeg。应用仍会打包，但提取 MP3、修复视频和 OCR 抽帧时会用中文提示用户安装。"
fi

if [ -x "$TESSERACT_PATH" ]; then
  echo "已找到 OCR：$TESSERACT_PATH"
else
  echo "提示：未找到 tesseract。应用仍会打包，但画面文字 OCR 时会用中文提示用户安装。"
fi

if "$PYTHON_BIN" -c "import faster_whisper" >/dev/null 2>&1; then
  echo "已找到语音识别：faster-whisper"
elif "$PYTHON_BIN" -c "import whisper" >/dev/null 2>&1; then
  echo "已找到语音识别：Whisper"
else
  echo "提示：未找到 Whisper / faster-whisper。应用仍会打包，但音频转文字时会用中文提示用户安装。"
fi

echo "正在清理旧的打包文件..."
rm -rf build "$APP_BUNDLE" "dist/$APP_NAME"
mkdir -p dist

PYINSTALLER_ARGS=(
  --windowed
  --noconfirm
  --clean
  --specpath "$PYINSTALLER_CONFIG_DIR"
  --collect-all customtkinter
  --collect-data certifi
  --collect-all faster_whisper
  --collect-all ctranslate2
  --collect-all tokenizers
  --collect-all onnxruntime
  --runtime-hook "$MACOS_RUNTIME_HOOK"
  --exclude-module torch
  --exclude-module torchvision
  --exclude-module torchaudio
  --exclude-module whisper
  --exclude-module numba
  --exclude-module llvmlite
  --exclude-module sympy
  --exclude-module tensorboard
  --osx-bundle-identifier "$BUNDLE_ID"
  --name "$APP_NAME"
)

if [ -n "$TARGET_ARCH" ]; then
  echo "目标架构：$TARGET_ARCH"
  PYINSTALLER_ARGS+=(--target-arch "$TARGET_ARCH")
fi

if [ -n "${ACAN_PYTHON_LIBRARY_DIR:-}" ]; then
  for runtime_library in libssl.3.dylib libcrypto.3.dylib libtcl8.6.dylib libtk8.6.dylib; do
    runtime_library_path="$ACAN_PYTHON_LIBRARY_DIR/$runtime_library"
    if [ ! -f "$runtime_library_path" ]; then
      echo "打包失败：缺少 Python 运行库 $runtime_library_path"
      exit 1
    fi
    PYINSTALLER_ARGS+=("--add-binary=${runtime_library_path}:.")
  done

  if [ ! -d "$ACAN_PYTHON_LIBRARY_DIR/tcl8.6" ] || [ ! -d "$ACAN_PYTHON_LIBRARY_DIR/tk8.6" ]; then
    echo "打包失败：缺少 Python Tcl/Tk 资源目录"
    exit 1
  fi
  PYINSTALLER_ARGS+=("--add-data=$ACAN_PYTHON_LIBRARY_DIR/tcl8.6:_tcl_data")
  PYINSTALLER_ARGS+=("--add-data=$ACAN_PYTHON_LIBRARY_DIR/tk8.6:_tk_data")
fi

if [ -n "${ACAN_BUNDLED_TOOLS_DIR:-}" ]; then
  BUNDLED_ROOT="$ACAN_BUNDLED_TOOLS_DIR"
  echo "正在把内置后台工具加入应用..."
  for tool_name in yt-dlp ffmpeg ffprobe deno; do
    tool_path="$BUNDLED_ROOT/tools/$tool_name"
    if [ ! -x "$tool_path" ]; then
      echo "打包失败：缺少内置工具 $tool_path"
      exit 1
    fi
    PYINSTALLER_ARGS+=("--add-binary=${tool_path}:tools")
  done


  for optional_tool_name in acan-vision-ocr tesseract; do
    optional_tool_path="$BUNDLED_ROOT/tools/$optional_tool_name"
    if [ -x "$optional_tool_path" ]; then
      PYINSTALLER_ARGS+=("--add-binary=${optional_tool_path}:tools")
    fi
  done

  if [ -d "$BUNDLED_ROOT/tools/lib" ]; then
    setopt null_glob
    for library_path in "$BUNDLED_ROOT"/tools/lib/*.dylib; do
      PYINSTALLER_ARGS+=("--add-binary=${library_path}:lib")
    done
  fi

  if [ -d "$BUNDLED_ROOT/tessdata" ]; then
    PYINSTALLER_ARGS+=("--add-data=$BUNDLED_ROOT/tessdata:tessdata")
  fi

  if [ -d "$BUNDLED_ROOT/licenses" ]; then
    PYINSTALLER_ARGS+=("--add-data=$BUNDLED_ROOT/licenses:licenses")
  fi
fi

if [ -f "$WHISPER_MODEL_DIR/model.bin" ]; then
  echo "正在把 faster-whisper base 模型加入应用..."
  PYINSTALLER_ARGS+=("--add-data=$WHISPER_MODEL_DIR:models/faster-whisper-base")
else
  echo "打包失败：缺少内置语音模型 $WHISPER_MODEL_DIR/model.bin"
  exit 1
fi

if [ -f "THIRD_PARTY_NOTICES.md" ]; then
  PYINSTALLER_ARGS+=("--add-data=$PWD/THIRD_PARTY_NOTICES.md:.")
fi

if [ -f "$ICON_PATH" ]; then
  echo "已找到图标：$ICON_PATH"
  PYINSTALLER_ARGS+=(--icon "$ICON_PATH")
else
  echo "未找到 icon.icns，将使用默认图标。"
fi

echo "正在打包 $APP_NAME.app..."
"$PYTHON_BIN" "$PYINSTALLER_RUNNER" "${PYINSTALLER_ARGS[@]}" main.py

if [ ! -d "$APP_BUNDLE" ]; then
  echo "正在生成 macOS 可双击 .app 外壳..."
  APP_CONTENTS="$APP_BUNDLE/Contents"
  APP_MACOS="$APP_CONTENTS/MacOS"
  APP_RESOURCES="$APP_CONTENTS/Resources"
  APP_PAYLOAD="$APP_RESOURCES/app"

  mkdir -p "$APP_MACOS" "$APP_RESOURCES"
  mv "dist/$APP_NAME" "$APP_PAYLOAD"
  if [ -f "$ICON_PATH" ]; then
    cp "$ICON_PATH" "$APP_RESOURCES/icon.icns"
  fi

  cat > "$APP_MACOS/$APP_NAME" <<'EOF'
#!/bin/zsh
APP_DIR="$(cd "$(dirname "$0")/../Resources/app" && pwd)"
cd "$APP_DIR"
exec "$APP_DIR/ACAN Studio"
EOF
  chmod +x "$APP_MACOS/$APP_NAME"

  cat > "$APP_CONTENTS/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>zh_CN</string>
  <key>CFBundleDisplayName</key>
  <string>ACAN Studio</string>
  <key>CFBundleExecutable</key>
  <string>ACAN Studio</string>
  <key>CFBundleIdentifier</key>
  <string>com.acan.studio</string>
  <key>CFBundleIconFile</key>
  <string>icon.icns</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>ACAN Studio</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF
  if [ ! -f "$APP_RESOURCES/icon.icns" ]; then
    /usr/libexec/PlistBuddy -c "Delete :CFBundleIconFile" "$APP_CONTENTS/Info.plist" >/dev/null 2>&1 || true
  fi
fi

/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion $MACOSX_DEPLOYMENT_TARGET" "$APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || \
  /usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string $MACOSX_DEPLOYMENT_TARGET" "$APP_BUNDLE/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$APP_BUNDLE/Contents/Info.plist"

if [ -d "dist/$APP_NAME" ] && [ -d "$APP_BUNDLE" ]; then
  rm -rf "dist/$APP_NAME"
fi

if [ ! -d "$APP_BUNDLE" ]; then
  echo "打包失败：没有生成 $APP_BUNDLE"
  exit 1
fi

if [ ! -x "$APP_EXECUTABLE" ]; then
  echo "打包失败：$APP_EXECUTABLE 不存在或不可执行"
  exit 1
fi

if /usr/libexec/PlistBuddy -c "Print :CFBundlePackageType" "$APP_BUNDLE/Contents/Info.plist" | grep -q "APPL"; then
  :
else
  echo "打包失败：Info.plist 不是有效的 macOS 应用配置"
  exit 1
fi

if [ "${ACAN_SKIP_INSTALL:-0}" = "1" ]; then
  echo "已跳过安装到 /Applications，保留 $APP_BUNDLE 供后续打包。"
else
  echo "正在安装最新版到 /Applications..."
  if cp -Rf "$APP_BUNDLE" "/Applications/"; then
    rm -rf "$APP_BUNDLE"
    killall Dock >/dev/null 2>&1 || true
  else
    echo "安装失败：无法复制 $APP_BUNDLE 到 /Applications/"
    echo "请检查是否有权限写入 /Applications，或手动把 $APP_BUNDLE 拖到应用程序文件夹。"
    exit 1
  fi
fi

echo ""
echo "打包完成"
if [ "${ACAN_SKIP_INSTALL:-0}" = "1" ]; then
  echo "已保留 $APP_BUNDLE"
else
  echo "已安装最新版到 $APPLICATIONS_APP"
  echo "已清理 dist 里的临时 App，避免 Launchpad 出现两个图标"
  echo "双击 /Applications/$APP_NAME.app 即可打开图形界面，不会弹出终端窗口。"
fi
echo "后台工具："
echo "  yt-dlp：$YTDLP_PATH"
echo "  ffmpeg ：$FFMPEG_PATH"
echo "  OCR    ：$TESSERACT_PATH"
echo "  Whisper：faster-whisper 或 openai-whisper"
