#!/usr/bin/env python3
"""
quiz_web.py — Geminiおまかせクイズゲーム（リッチWeb UI版）

出題ロジックは scripts/quiz_game.py を唯一の正本として import 再利用する（二重実装しない）。
UIは scripts/quiz_webui/ の HTML/CSS/JS（同梱・CDN不使用＝オフライン動作）。
quota作法（ask前に確認・core.QUOTA_STOP_THRESHOLD 以下は停止）を維持する。

セキュリティ: 127.0.0.1限定 / 起動時ワンタイムトークン / Host検証 / 静的配信は既知3ファイルのみ
/ POSTは同一オリジン要求 / LLM生成文字列はクライアント側で textContent のみ（innerHTML不使用）。

使い方:
    python scripts/quiz_web.py                 # 起動してブラウザを開く
    python scripts/quiz_web.py --no-browser    # URLを表示するだけ
    python scripts/quiz_web.py --stub          # agyを使わないデモ（quota消費ゼロ）
    python scripts/quiz_web.py --port 8765
"""

import argparse
import json
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import quiz_game as core

WEBUI_DIRNAME = "quiz_webui"
TOKEN_PLACEHOLDER = "__QUIZ_TOKEN__"
MAX_BODY = 64 * 1024
MAX_NUM = 10
HOSTS = ("127.0.0.1", "localhost")

ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
    "form-action 'none'; object-src 'none'; frame-ancestors 'none'"
)


def resource_dir():
    """静的資産の所在。frozen時はPyInstaller展開先、通常時はscripts/quiz_webui/。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidate = base / WEBUI_DIRNAME
        if candidate.is_dir():
            return candidate
        return Path(sys.executable).resolve().parent / WEBUI_DIRNAME
    return Path(__file__).resolve().parent / WEBUI_DIRNAME


class Job:
    """1回の出題生成ジョブ。状態は /api/status で開示する。"""

    def __init__(self):
        self.lock = threading.Lock()
        self.gen = 0
        self.reset()

    def reset(self):
        with self.lock:
            self.state = "idle"  # idle | running | done | error
            self.started = 0.0
            self.num = 0
            self.retrying = False
            self.questions = []
            self.meta = ""
            self.diff = 0
            self.diff_name = ""
            self.theme = ""
            self.error = ""

    def snapshot(self, timeout_for):
        with self.lock:
            elapsed = int(time.time() - self.started) if self.state == "running" else 0
            estimate = int(timeout_for(self.num)) if self.num else 0
            return {
                "state": self.state,
                "elapsed": elapsed,
                "estimate": estimate,
                "retrying": self.retrying,
                "num": self.num,
                "theme": self.theme,
                "diff": self.diff,
                "diff_name": self.diff_name,
                "meta": self.meta,
                "questions": self.questions if self.state == "done" else [],
                "error": self.error,
            }


class ServerState:
    def __init__(self, core_module, token, stub=False):
        self.core = core_module
        self.token = token
        self.stub = stub
        self.job = Job()


class QuizHandler(BaseHTTPRequestHandler):
    server_version = "QuizWeb/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    @property
    def state(self):
        return self.server.state

    # -- helpers --
    def _port(self):
        return self.server.server_address[1]

    def _host_ok(self):
        host = self.headers.get("Host", "")
        port = self._port()
        return host in {"%s:%d" % (h, port) for h in HOSTS}

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True  # ブラウザ以外（curl等）。トークン照合で担保する
        port = self._port()
        return origin in {"http://%s:%d" % (h, port) for h in HOSTS}

    def _token_ok(self):
        got = self.headers.get("X-Quiz-Token", "")
        return bool(got) and secrets.compare_digest(got, self.state.token)

    def _send(self, code, body, ctype, extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if code != 204:
            self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD" and code != 204:
            self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False),
                   "application/json; charset=utf-8",
                   extra={"Content-Security-Policy": CSP})

    def _text(self, code, text):
        self._send(code, text, "text/plain; charset=utf-8")

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.close_connection = True
            return None, "Content-Length不正"
        if length < 0 or length > MAX_BODY:
            self.close_connection = True  # 未読本文をkeep-aliveの次リクエストと誤解させない
            return None, "本文が大きすぎます"
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8")), None
        except (ValueError, UnicodeDecodeError):
            self.close_connection = True
            return None, "JSONを解釈できません"

    # -- static --
    def _serve_asset(self, req_path):
        name, ctype = ASSETS[req_path]
        path = resource_dir() / name
        try:
            data = path.read_bytes()
        except OSError:
            return self._text(500, "静的資産が見つかりません: {}".format(name))
        if name == "index.html":
            data = data.replace(
                TOKEN_PLACEHOLDER.encode("utf-8"),
                self.state.token.encode("utf-8"))
        self._send(200, data, ctype, extra={"Content-Security-Policy": CSP})

    # -- config / quota / status --
    def _config(self):
        c = self.state.core
        return {
            "app": "quiz-rich",
            "difficulties": [
                {"value": k, "name": v[0]} for k, v in sorted(c.DIFFICULTY.items())
            ],
            "default_num": c.DEFAULT_NUM,
            "default_difficulty": c.DEFAULT_DIFFICULTY,
            "max_num": MAX_NUM,
            "stop_threshold": c.QUOTA_STOP_THRESHOLD,
            "stub": self.state.stub,
        }

    def _quota(self):
        c = self.state.core
        try:
            agy, err = c.require_agy()
        except Exception as exc:
            return {"available": False, "error": str(exc)}
        if agy is None:
            return {"available": False, "error": err}
        quota = c.ask_quota(agy)
        five = quota.get("gemini_5h")
        return {"available": five is not None, "gemini_5h": five}

    # -- job --
    def _start_job(self, theme, num, difficulty):
        c = self.state.core
        job = self.state.job
        with job.lock:
            if job.state == "running":
                return False
            job.gen += 1
            my_gen = job.gen
            job.state = "running"
            job.started = time.time()
            job.num = num
            job.retrying = False
            job.questions = []
            job.meta = ""
            job.error = ""
            job.diff = difficulty
            job.theme = theme

        def publish(**fields):
            """世代が一致する時だけ状態を反映する（キャンセル後の結果を破棄）。"""
            with job.lock:
                if job.gen != my_gen:
                    return
                for key, value in fields.items():
                    setattr(job, key, value)

        def worker():
            try:
                agy, err = c.require_agy()
                if agy is None:
                    raise RuntimeError(err or "agy が見つかりません")
                quota = c.ask_quota(agy)
                five = quota.get("gemini_5h")
                if five is not None and five <= c.QUOTA_STOP_THRESHOLD:
                    publish(state="error", error="残量{}%のため開始しません（{}%以下は停止）。".format(
                        five, c.QUOTA_STOP_THRESHOLD))
                    return
                questions, meta = c.fetch_questions(
                    agy, c.base_dir(), theme, num, difficulty,
                    on_retry=lambda: publish(retrying=True))
                if not questions:
                    publish(state="error", error="出題の生成に失敗: {}".format(meta))
                    return
                publish(questions=questions, meta=meta,
                        diff_name=c.DIFFICULTY[difficulty][0], state="done")
            except Exception as exc:  # agy不調・予期せぬ失敗をUIへ明示
                publish(state="error", error="生成中に失敗: {}".format(exc))

        threading.Thread(target=worker, daemon=True).start()
        return True

    def _save(self, body):
        job = self.state.job
        with job.lock:
            if job.state != "done" or not job.questions:
                return None, "保存できる結果がありません"
            questions = list(job.questions)
            theme = job.meta or job.theme
            diff_name = job.diff_name
        picks = body.get("picks")
        score = body.get("score")
        if (not isinstance(picks, list) or len(picks) != len(questions)
                or not all(isinstance(p, int) and 0 <= p <= 3 for p in picks)
                or not isinstance(score, int) or not 0 <= score <= len(questions)):
            return None, "保存データが不正です"
        import datetime
        now = datetime.datetime.now()
        path = self.state.core.base_dir() / "quiz_{}.txt".format(
            now.strftime("%Y%m%d_%H%M%S"))
        text = self.state.core.format_result_text(
            theme, diff_name, score, questions, picks, now=now)
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            return None, "保存できません: {}".format(exc)
        return str(path), None

    # -- routes --
    def do_GET(self):
        if not self._host_ok():
            return self._text(403, "forbidden")
        path = urlparse(self.path).path
        if path in ASSETS:
            return self._serve_asset(path)
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if path.startswith("/api/"):
            if not self._token_ok():
                return self._json(403, {"error": "トークンが不正です"})
            if path == "/api/config":
                return self._json(200, self._config())
            if path == "/api/quota":
                return self._json(200, self._quota())
            if path == "/api/status":
                c = self.state.core
                return self._json(200, self.state.job.snapshot(c.timeout_for))
        return self._text(404, "not found")

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            return self._text(403, "forbidden")
        if not self._token_ok():
            return self._json(403, {"error": "トークンが不正です"})
        path = urlparse(self.path).path
        if path not in ("/api/questions", "/api/comment", "/api/save",
                        "/api/cancel", "/api/shutdown"):
            return self._text(404, "not found")
        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err})
        if path == "/api/questions":
            return self._post_questions(body)
        if path == "/api/comment":
            return self._post_comment(body)
        if path == "/api/save":
            return self._post_save(body)
        if path == "/api/cancel":
            return self._post_cancel()
        return self._post_shutdown()

    def _post_cancel(self):
        """実行中の生成結果を破棄して idle に戻す（agy呼出はtimeoutまで継続し得る）。"""
        job = self.state.job
        with job.lock:
            job.gen += 1
            job.state = "idle"
            job.retrying = False
            job.questions = []
            job.meta = ""
            job.error = ""
        return self._json(200, {"ok": True})

    def _post_questions(self, body):
        c = self.state.core
        theme = body.get("theme", "")
        if not isinstance(theme, str):
            return self._json(400, {"error": "themeが不正です"})
        theme = theme.strip()
        if len(theme) > 60:
            return self._json(400, {"error": "テーマが長すぎます（60文字以内）"})
        try:
            num = int(body.get("num", c.DEFAULT_NUM))
        except (TypeError, ValueError):
            return self._json(400, {"error": "numが不正です"})
        difficulty = body.get("difficulty", c.DEFAULT_DIFFICULTY)
        if not 1 <= num <= MAX_NUM or difficulty not in c.DIFFICULTY:
            return self._json(400, {"error": "numまたはdifficultyが範囲外です"})
        if not self._start_job(theme, num, difficulty):
            return self._json(409, {"error": "既に生成中です"})
        return self._json(202, {"accepted": True})

    def _post_comment(self, body):
        c = self.state.core
        score, total = body.get("score"), body.get("total")
        theme, diff = body.get("theme", ""), body.get("diff", "")
        if (not isinstance(score, int) or not isinstance(total, int)
                or total < 0 or not 0 <= score <= total
                or not isinstance(theme, str) or not isinstance(diff, str)):
            return self._json(400, {"error": "comment入力が不正です"})
        return self._json(200, {"comment": c.comment_for(score, total, theme, diff)})

    def _post_save(self, body):
        path, err = self._save(body)
        if err:
            return self._json(400, {"error": err})
        return self._json(200, {"path": path})

    def _post_shutdown(self):
        # 応答を返してから別スレッドで停止する（serve_foreverと同一スレッドでの停止を避ける）
        self._json(200, {"ok": True, "message": "サーバを終了します"})
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def create_server(core_module=core, host="127.0.0.1", port=0, stub=False):
    """テスト・通常起動の共通入口。戻り: (httpd, token, port)。"""
    token = secrets.token_urlsafe(32)
    httpd = ThreadingHTTPServer((host, port), QuizHandler)
    httpd.daemon_threads = True
    httpd.state = ServerState(core_module, token, stub)
    return httpd, token, httpd.server_address[1]


def _install_stub(core_module):
    """--stub用。agyを呼ばずサンプル問を返す（UIの手動確認用・quota消費ゼロ）。"""
    sample = [
        {
            "q": "デモ問題1: 1 + 1 は？",
            "choices": ["1", "2", "3", "4"],
            "answer": 1,
            "explanation": "1 + 1 = 2 です。",
        },
        {
            "q": "デモ問題2: 日本の首都は？",
            "choices": ["大阪", "京都", "東京", "名古屋"],
            "answer": 2,
            "explanation": "日本の首都は東京です。",
        },
        {
            "q": "デモ問題3: 水の化学式は？",
            "choices": ["CO2", "H2O", "O2", "NaCl"],
            "answer": 1,
            "explanation": "水は H2O です。",
        },
    ]
    core_module.require_agy = lambda: (object(), "")
    core_module.ask_quota = lambda agy: {"gemini_5h": 80}

    def fake_fetch(agy, cwd, theme, num, difficulty, verbose=False, on_retry=None):
        time.sleep(2.0)
        return sample[:max(1, min(num, len(sample)))], "デモ（stub）"

    core_module.fetch_questions = fake_fetch


def main(argv=None):
    parser = argparse.ArgumentParser(description="Geminiおまかせクイズ（リッチWeb UI版）")
    parser.add_argument("--port", type=int, default=0, help="待受ポート（既定: 空きを自動選択）")
    parser.add_argument("--no-browser", action="store_true", help="ブラウザを自動で開かない")
    parser.add_argument("--stub", action="store_true", help="agyを使わないデモモード")
    args = parser.parse_args(argv)

    core.safe_console()
    if args.stub:
        _install_stub(core)

    httpd, token, port = create_server(port=args.port, stub=args.stub)
    url = "http://127.0.0.1:{}/".format(port)
    print("Quiz (rich web UI) 起動: {}".format(url))
    missing = [name for name in ("index.html", "style.css", "app.js")
               if not (resource_dir() / name).is_file()]
    if missing:
        print("警告: 静的資産が不足しています: {}".format(", ".join(missing)))
    if args.stub:
        print("デモモード（agy不使用・quota消費ゼロ）")

    if not args.no_browser:
        try:
            opened = webbrowser.open(url)
        except Exception:
            opened = False
        if not opened:
            print("ブラウザを自動で開けませんでした。上のURLを手動で開いてください。")

    print("終了するには Ctrl+C（または画面の「終了」）。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
