"""User-facing failure suggestions that do not depend on the GUI."""

from __future__ import annotations


LOGIN_COOKIE_KEYWORDS = (
    "fresh cookies are needed",
    "failed to parse json",
    "login required",
    "sign in",
    "authentication",
    "cookie",
    "cookies",
)
WEIBO_VISITOR_ERROR_KEYWORDS = (
    "passport.weibo.com/visitor",
    "visitor/visitor",
    "login",
)
WEIBO_VISITOR_ERROR_MESSAGE = "微博把下载请求跳转到了登录/访客验证页。请在 Chrome 打开微博网页版，确认已登录，刷新该视频页面并能正常播放后再重试。"
DOUYIN_COOKIE_PARSE_ERROR_KEYWORDS = ("fresh cookies", "failed to parse json", "failed to download web detail json")
DOUYIN_UNSUPPORTED_ERROR_KEYWORDS = ("unsupported url",)
DOUYIN_NETWORK_ERROR_KEYWORDS = ("http error", "timeout", "connection")


def _is_login_or_cookie_error(output: str) -> bool:
    normalized = (output or "").lower()
    return any(keyword in normalized for keyword in LOGIN_COOKIE_KEYWORDS)


def _is_weibo_visitor_error(output: str) -> bool:
    normalized = (output or "").lower()
    return any(keyword in normalized for keyword in WEIBO_VISITOR_ERROR_KEYWORDS)


def platform_stage_suggestion(platform_name: str, stage: str, output: str) -> str:
    """Return the Chinese next-step suggestion for a failed workflow stage."""

    normalized_output = (output or "").lower()
    if "certificate_verify_failed" in normalized_output:
        return "HTTPS 证书校验失败。请使用包含信任证书的新版 ACAN Studio；如仍失败，请检查系统时间和网络代理的证书配置。"
    if platform_name == "YouTube":
        javascript_error_tokens = (
            "n challenge solving failed",
            "supported javascript runtime",
            "challenge solver script distribution",
            "the page needs to be reloaded",
        )
        if any(token in normalized_output for token in javascript_error_tokens):
            return "YouTube 播放器的 JavaScript 挑战解析没有成功运行。请使用内置 Deno 与 EJS 组件的最新版 ACAN Studio，重新打开视频页面后再试；如果仍失败，请把完整日志发给开发者。"
        ssl_error_tokens = (
            "unexpected_eof_while_reading",
            "eof occurred in violation of protocol",
            "ssl connection",
            "tls connection",
        )
        if any(token in normalized_output for token in ssl_error_tokens):
            return "YouTube 视频已经解析成功，但网络或代理提前切断了加密传输。最新版会自动依次尝试分块断点续传、小分块续传和 curl 备用传输；如果仍失败，请切换代理节点或网络后重试，已有的 .part 文件会继续续传。"
        if _is_login_or_cookie_error(output):
            return "该 YouTube 视频可能需要登录或年龄验证。请在 Mac 的 Chrome 中登录可正常观看该视频的账号，并在设置中启用浏览器 Cookie 后重试。"
        return "请确认 YouTube 视频是公开可播放的，检查网络后重新尝试。"

    if platform_name == "抖音":
        if any(token in normalized_output for token in DOUYIN_COOKIE_PARSE_ERROR_KEYWORDS):
            return ("抖音接口未返回视频数据（可能为 403 拒绝访问或会话校验失败）。"
                    "下载器的 Fresh cookies 提示不等于未登录，即使命令带有 Cookie 也可能出现。\n"
                    "请在设置所选浏览器中打开同一视频，完成网页提示的验证并确认能播放，"
                    "再回到 ACAN Studio 重试；如果仍返回 403，可能需要下载器适配，重复登录不保证解决。\n"
                    "DMG 内置下载器随 ACAN Studio 更新；更新 Homebrew 中的 yt-dlp 不会更新 App 内的版本。")
        if any(token in normalized_output for token in DOUYIN_UNSUPPORTED_ERROR_KEYWORDS):
            return "当前链接类型暂不支持，请进入视频详情页后重新复制分享链接。\n抖音链接已成功识别，请稍后更新 yt-dlp 后重试，或使用备用下载方案。"
        if any(token in normalized_output for token in DOUYIN_NETWORK_ERROR_KEYWORDS):
            return "网络异常或平台限制，请稍后重试。\n抖音链接已成功识别，请稍后更新 yt-dlp 后重试，或使用备用下载方案。"
        return "抖音下载失败，请确认链接是公开视频页；如果 yt-dlp 仍无法解析，可稍后更新 yt-dlp 或使用备用下载方案。"

    if platform_name == "微博":
        if _is_weibo_visitor_error(output):
            return WEIBO_VISITOR_ERROR_MESSAGE
        if stage == "下载":
            return "微博视频下载失败，请检查链接是否公开、是否需要登录，或稍后重试。"
        if stage == "转码":
            return "视频已下载，但转码修复失败，请查看 ffmpeg 日志。"
        if stage == "OCR":
            return "OCR 失败，请确认本地视频已经下载成功，并检查 OCR 引擎是否可用。"
        if stage == "音频转文字":
            return "音频转文字失败，请确认视频有可识别音轨，并检查 Whisper/faster-whisper 是否可用。"
        return "微博处理失败，请检查链接是否公开、是否需要登录，或稍后重试。"

    if platform_name == "小红书" and _is_login_or_cookie_error(output):
        return "手机 App 登录状态不能被电脑读取，请在 Mac 的 Chrome 中登录小红书网页版后重试。"

    if platform_name == "芒果TV":
        if any(token in normalized_output for token in ("drm", "widevine", "protected content")):
            return "该芒果TV视频受平台版权保护。即使账号拥有 SVIP，ACAN Studio 也不能绕过此类保护，请在芒果TV官方网页或 App 内观看。"
        if "unsupported url" in normalized_output:
            return "芒果TV链接暂时无法被 yt-dlp 解析。请确认复制的是视频播放页地址，不是首页、专题页或搜索页；也可以更新 yt-dlp 后重试。"
        if _is_login_or_cookie_error(output) or any(token in normalized_output for token in ("403", "forbidden", "login", "vip", "付费")):
            return "芒果TV可能需要网页登录或会员权限。请在 Chrome 登录拥有会员权益的账号，并确认该视频能正常播放后再重试；受版权保护的视频无法通过本工具导出。"
        return "芒果TV下载失败，请确认链接是公开视频播放页、网络正常，并尝试更新 yt-dlp。完整错误日志已保留。"

    if stage == "转码":
        return "视频已下载，但转码修复失败，请查看 ffmpeg 日志。"
    if stage == "OCR":
        return "OCR 失败，请确认本地视频已经下载成功，并检查 OCR 引擎是否可用。"
    if stage == "音频转文字":
        return "音频转文字失败，请确认视频有可识别音轨，并检查 Whisper/faster-whisper 是否可用。"
    if _is_login_or_cookie_error(output):
        return "当前平台可能需要登录，请在 Mac 的 Chrome 中登录对应平台网页版后重试。"
    return "请检查链接是否公开、网络是否正常，或稍后重试。"
