import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import ProxyHandler

from acan_studio.core.network import create_https_context, create_https_opener
from acan_studio.core.errors import platform_stage_suggestion


class HTTPSRegressionTests(unittest.TestCase):
    def test_bundle_supplies_roots_when_python_default_path_is_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"SSL_CERT_FILE": directory + "/absent.pem", "SSL_CERT_DIR": directory}):
                self.assertEqual(ssl.create_default_context().cert_store_stats()["x509_ca"], 0)
                context = create_https_context()
                self.assertGreater(context.cert_store_stats()["x509_ca"], 0)
                self.assertTrue(context.check_hostname)
                self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    @unittest.skipUnless(shutil.which("openssl"), "openssl required for local TLS fixture")
    def test_explicit_ca_is_preserved_but_untrusted_certificates_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            certificate, key = root / "cert.pem", root / "key.pem"
            subprocess.run([shutil.which("openssl"), "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                            "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
                            "-keyout", str(key), "-out", str(certificate)],
                           check=True, capture_output=True, timeout=20)

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"verified")

                def log_message(self, *args):
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certificate, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"https://localhost:{server.server_port}/"
                with patch.dict(os.environ, {"SSL_CERT_FILE": str(certificate), "SSL_CERT_DIR": directory}):
                    with create_https_opener(ProxyHandler({})).open(url, timeout=3) as response:
                        self.assertEqual(response.read(), b"verified")
                with patch.dict(os.environ, {"SSL_CERT_FILE": str(root / "missing"), "SSL_CERT_DIR": directory}):
                    with self.assertRaises(URLError) as raised:
                        create_https_opener(ProxyHandler({})).open(url, timeout=3)
                    self.assertIsInstance(raised.exception.reason, ssl.SSLCertVerificationError)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_exact_douyin_cookie_error_is_not_misdiagnosed_as_missing_login(self):
        output = ("Failed to download web detail JSON: HTTP Error 403: Forbidden\n"
                  "Fresh cookies (not necessarily logged in) are needed")
        message = platform_stage_suggestion("抖音", "下载", output)
        self.assertIn("不等于未登录", message)
        self.assertIn("403", message)
        self.assertNotIn("yt-dlp -U", message)

    def test_certificate_error_takes_precedence_over_cookie_hint(self):
        message = platform_stage_suggestion("抖音", "下载", "CERTIFICATE_VERIFY_FAILED; Fresh cookies")
        self.assertIn("证书", message)
        self.assertNotIn("请在 Chrome 登录", message)
