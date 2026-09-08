#!/bin/zsh
set -e

cd "$(dirname "$0")"

PYTHON_BIN="${ACAN_PYTHON_BIN:-.venv/bin/python}"
REQUIREMENTS_FILE="${ACAN_REQUIREMENTS_FILE:-requirements.txt}"
BUNDLE_ROOT="$PWD/.pyinstaller-cache/embedded-tools"
YTDLP_ENTRY="$PWD/packaging/yt_dlp_entry.py"
YTDLP_BUILD_DIR="$PWD/.pyinstaller-cache/yt-dlp-tool-build"
YTDLP_PATCH="$PWD/patches/yt-dlp-2026.08.19-mgtv-web-player.patch"
YTDLP_VERSION="2026.8.19"
YTDLP_MGTV_PATCH_MARKER="ACAN_MGTV_PATCH_V2"
WHISPER_MODEL_DIR="$PWD/.pyinstaller-cache/models/faster-whisper-base"
TARGET_ARCH="${ACAN_TARGET_ARCH:-$(uname -m)}"
VISION_OCR_SOURCE="$PWD/packaging/acan_vision_ocr.swift"
PYINSTALLER_RUNNER="$PWD/packaging/run_pyinstaller.py"
PORTABLE_FFMPEG_RELEASE="b6.1.1"
PORTABLE_TOOLS_CACHE="$PWD/.pyinstaller-cache/portable-tools/$PORTABLE_FFMPEG_RELEASE/$TARGET_ARCH"
DENO_RELEASE="v2.9.6"
DENO_CACHE="$PWD/.pyinstaller-cache/portable-tools/deno/$DENO_RELEASE/$TARGET_ARCH"
export MACOSX_DEPLOYMENT_TARGET="${ACAN_MACOSX_DEPLOYMENT_TARGET:-11.0}"

download_verified_url() {
  local url="$1"
  local expected_sha256="$2"
  local destination="$3"
  local asset_name="$4"

  mkdir -p "$(dirname "$destination")"

  if [ -f "$destination" ]; then
    local existing_sha256
    existing_sha256="$(shasum -a 256 "$destination" | awk '{print $1}')"
    if [ "$existing_sha256" = "$expected_sha256" ]; then
      return
    fi
    mv "$destination" "$destination.invalid.$(date +%Y%m%d%H%M%S)"
  fi

  local temporary_download="$destination.download"
  curl --http1.1 --retry 10 --retry-all-errors --connect-timeout 30 --continue-at - --fail --location --silent --show-error \
    -o "$temporary_download" \
    "$url"

  local actual_sha256
  actual_sha256="$(shasum -a 256 "$temporary_download" | awk '{print $1}')"
  if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "下载校验失败：$asset_name"
    echo "期望：$expected_sha256"
    echo "实际：$actual_sha256"
    exit 1
  fi
  mv "$temporary_download" "$destination"
}

download_verified_asset() {
  local asset_name="$1"
  local expected_sha256="$2"
  download_verified_url \
    "https://github.com/eugeneware/ffmpeg-static/releases/download/$PORTABLE_FFMPEG_RELEASE/$asset_name" \
    "$expected_sha256" \
    "$PORTABLE_TOOLS_CACHE/$asset_name" \
    "$asset_name"
}

if [ ! -x "$PYTHON_BIN" ]; then
  if [ -n "${ACAN_PYTHON_BIN:-}" ]; then
    echo "打包失败：指定的 Python 不可执行：$PYTHON_BIN"
    exit 1
  fi
  python3 -m venv .venv
fi

"$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$REQUIREMENTS_FILE"

YTDLP_PACKAGE_DIR="$("$PYTHON_BIN" -c 'import os, yt_dlp; print(os.path.dirname(yt_dlp.__file__))')"
YTDLP_MGTV_EXTRACTOR="$YTDLP_PACKAGE_DIR/extractor/mgtv.py"
if [ ! -f "$YTDLP_PATCH" ]; then
  echo "缺少芒果TV兼容补丁：$YTDLP_PATCH"
  exit 1
fi

echo "正在应用芒果TV会员流兼容补丁..."
if grep -q "f'did={did}|pno=1030" "$YTDLP_MGTV_EXTRACTOR" && \
   ! grep -q "$YTDLP_MGTV_PATCH_MARKER" "$YTDLP_MGTV_EXTRACTOR"; then
  echo "检测到旧版芒果TV补丁，正在恢复官方解析器后升级补丁..."
  "$PYTHON_BIN" -m pip install --disable-pip-version-check --force-reinstall --no-deps "yt-dlp==$YTDLP_VERSION"
fi

if grep -q "$YTDLP_MGTV_PATCH_MARKER" "$YTDLP_MGTV_EXTRACTOR" && \
   grep -q "'definitionType': '2'" "$YTDLP_MGTV_EXTRACTOR" && \
   grep -q "'mgtv_access_hint':" "$YTDLP_MGTV_EXTRACTOR"; then
  echo "芒果TV兼容补丁已经应用，继续构建。"
elif /usr/bin/patch -N -t -p0 -d "$YTDLP_PACKAGE_DIR" -i "$YTDLP_PATCH"; then
  :
else
  echo "无法应用芒果TV兼容补丁；请确认 $REQUIREMENTS_FILE 中的 yt-dlp 版本未被修改。"
  exit 1
fi

if [ ! -f "$WHISPER_MODEL_DIR/model.bin" ]; then
  echo "正在下载 faster-whisper base 多语言模型..."
  mkdir -p "$WHISPER_MODEL_DIR"
  "$PYTHON_BIN" -c 'import sys; from huggingface_hub import snapshot_download; snapshot_download(repo_id="Systran/faster-whisper-base", local_dir=sys.argv[1])' "$WHISPER_MODEL_DIR"
fi

case "$TARGET_ARCH" in
  arm64)
    FFMPEG_ASSET="ffmpeg-darwin-arm64"
    NOTICE_ASSET="darwin-arm64.README"
    LICENSE_ASSET="darwin-arm64.LICENSE"
    FFMPEG_SHA256="a90e3db6a3fd35f6074b013f948b1aa45b31c6375489d39e572bea3f18336584"
    NOTICE_SHA256="05ba4b92c96605434b1aaae3eedf5a2c280c9607bf78ffca9a5b536d9af2dc6a"
    LICENSE_SHA256="cb48bf09a11f5fb576cddb0431c8f5ed0a60157a9ec942adffc13907cbe083f2"
    DENO_ASSET="deno-aarch64-apple-darwin.zip"
    DENO_SHA256="213a2f304f04d3c9cb5220669afad138f60a5aab1fe80962abdeb8f35807a472"
    ;;
  x86_64)
    FFMPEG_ASSET="ffmpeg-darwin-x64"
    NOTICE_ASSET="darwin-x64.README"
    LICENSE_ASSET="darwin-x64.LICENSE"
    FFMPEG_SHA256="ebdddc936f61e14049a2d4b549a412b8a40deeff6540e58a9f2a2da9e6b18894"
    NOTICE_SHA256="e88a0325f8e5b75210355e37341824f074d3cd82def2125be54c914b62848a36"
    LICENSE_SHA256="2e1d16c72fd74e12063776371da757322f8b77589386532f4fd8634bde7de1af"
    DENO_ASSET="deno-x86_64-apple-darwin.zip"
    DENO_SHA256="7d4524b82bcc557fe020a1a5b56956ed42b992ae5b28026e8ad5d17329533f5f"
    ;;
  *)
    echo "不支持的目标架构：$TARGET_ARCH"
    exit 1
    ;;
esac

mkdir -p "$PORTABLE_TOOLS_CACHE"
echo "正在准备已校验的静态 ffmpeg/ffprobe（$TARGET_ARCH）..."
download_verified_asset "$FFMPEG_ASSET" "$FFMPEG_SHA256"
download_verified_asset "$NOTICE_ASSET" "$NOTICE_SHA256"
download_verified_asset "$LICENSE_ASSET" "$LICENSE_SHA256"
PORTABLE_FFPROBE_PATH="$(./packaging/build_portable_ffprobe.sh "$TARGET_ARCH" "$MACOSX_DEPLOYMENT_TARGET")"

echo "正在准备已校验的 Deno JavaScript 运行时（$TARGET_ARCH）..."
DENO_ARCHIVE="$DENO_CACHE/$DENO_ASSET"
DENO_BINARY="$DENO_CACHE/deno"
download_verified_url \
  "https://github.com/denoland/deno/releases/download/$DENO_RELEASE/$DENO_ASSET" \
  "$DENO_SHA256" \
  "$DENO_ARCHIVE" \
  "$DENO_ASSET"

if [ ! -x "$DENO_BINARY" ] || ! file "$DENO_BINARY" | grep -q "$TARGET_ARCH"; then
  DENO_EXTRACT_DIR="$(mktemp -d -t acan-deno)"
  ditto -x -k "$DENO_ARCHIVE" "$DENO_EXTRACT_DIR"
  if [ ! -f "$DENO_EXTRACT_DIR/deno" ]; then
    echo "Deno 解压失败：归档中没有 deno 可执行文件。"
    rm -rf "$DENO_EXTRACT_DIR"
    exit 1
  fi
  cp -L "$DENO_EXTRACT_DIR/deno" "$DENO_BINARY"
  chmod +x "$DENO_BINARY"
  rm -rf "$DENO_EXTRACT_DIR"
fi

if ! file "$DENO_BINARY" | grep -q "$TARGET_ARCH"; then
  echo "Deno 架构校验失败：需要 $TARGET_ARCH"
  file "$DENO_BINARY"
  exit 1
fi

rm -rf "$BUNDLE_ROOT" "$YTDLP_BUILD_DIR"
mkdir -p "$BUNDLE_ROOT/tools" "$BUNDLE_ROOT/licenses"

if [ ! -f "$VISION_OCR_SOURCE" ]; then
  echo "缺少 macOS Vision OCR 源码：$VISION_OCR_SOURCE"
  exit 1
fi

echo "正在生成内置 macOS Vision OCR（$TARGET_ARCH，macOS $MACOSX_DEPLOYMENT_TARGET+）..."
xcrun swiftc \
  -O \
  -target "${TARGET_ARCH}-apple-macos${MACOSX_DEPLOYMENT_TARGET}" \
  "$VISION_OCR_SOURCE" \
  -o "$BUNDLE_ROOT/tools/acan-vision-ocr"

echo "正在生成独立 yt-dlp..."
"$PYTHON_BIN" -c 'import yt_dlp_ejs' || {
  echo "打包失败：yt-dlp-ejs 未正确安装。"
  exit 1
}
YTDLP_PYINSTALLER_ARGS=(
  --onefile \
  --noconfirm \
  --clean \
  --name yt-dlp \
  --distpath "$BUNDLE_ROOT/tools" \
  --workpath "$YTDLP_BUILD_DIR" \
  --specpath "$PWD/.pyinstaller-cache" \
  --collect-all yt_dlp
  --collect-all yt_dlp_ejs
  --target-arch "$TARGET_ARCH"
)

if [ -n "${ACAN_PYTHON_LIBRARY_DIR:-}" ]; then
  for ssl_library in libssl.3.dylib libcrypto.3.dylib; do
    ssl_library_path="$ACAN_PYTHON_LIBRARY_DIR/$ssl_library"
    if [ ! -f "$ssl_library_path" ]; then
      echo "打包失败：缺少 Python HTTPS 运行库 $ssl_library_path"
      exit 1
    fi
    YTDLP_PYINSTALLER_ARGS+=("--add-binary=${ssl_library_path}:.")
  done
fi
"$PYTHON_BIN" "$PYINSTALLER_RUNNER" "${YTDLP_PYINSTALLER_ARGS[@]}" "$YTDLP_ENTRY"

cp -L "$PORTABLE_TOOLS_CACHE/$FFMPEG_ASSET" "$BUNDLE_ROOT/tools/ffmpeg"
cp -L "$PORTABLE_FFPROBE_PATH" "$BUNDLE_ROOT/tools/ffprobe"
cp -L "$DENO_BINARY" "$BUNDLE_ROOT/tools/deno"
cp -L "$PORTABLE_TOOLS_CACHE/$NOTICE_ASSET" "$BUNDLE_ROOT/licenses/ffmpeg-static.README"
cp -L "$PORTABLE_TOOLS_CACHE/$LICENSE_ASSET" "$BUNDLE_ROOT/licenses/ffmpeg-static.LICENSE"
cp -L "$PWD/packaging/licenses/DENO-LICENSE.md" "$BUNDLE_ROOT/licenses/DENO-LICENSE.md"
chmod +x "$BUNDLE_ROOT/tools/ffmpeg" "$BUNDLE_ROOT/tools/ffprobe" "$BUNDLE_ROOT/tools/deno"

if command -v xattr >/dev/null 2>&1; then
  xattr -cr "$BUNDLE_ROOT" || true
fi

echo "内置工具准备完成：$BUNDLE_ROOT"
