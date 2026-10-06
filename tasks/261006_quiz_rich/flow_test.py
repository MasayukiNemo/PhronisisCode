#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flow_test.py — quiz_web.py のHTTP/API/セキュリティ検証（stub・quota消費ゼロ）

quiz_game の agy 依存関数をstubに差替え、port=0でサーバを起動して
全API遷移・403系・保存・comment_for呼出・停止を urllib で検証する。
DOM/アニメの自動検証はstdlibでは不可（手動確認に切分。log参照）。
"""
import json
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import quiz_game
import quiz_web

RESULTS = []
TEST_TMP = None


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    line = "[{}] {}".format(mark, name)
    if detail and not ok:
        line += " :: " + detail
    print(line)


def make_questions(n):
    qs = []
    for i in range(n):
        qs.append({
            "q": "問題{}".format(i + 1),
            "choices": ["A{}".format(i), "B{}".format(i), "C{}".format(i), "D{}".format(i)],
            "answer": i % 4,
            "explanation": "解説{}".format(i + 1),
        })
    return qs


def check_dom_ids():
    webui = Path(__file__).resolve().parents[2] / "scripts" / "quiz_webui"
    js = (webui / "app.js").read_text(encoding="utf-8")
    html = (webui / "index.html").read_text(encoding="utf-8")
    html_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
    used = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', js))
    missing = sorted(used - html_ids)
    check("DOM id整合（app.js→index.html）", not missing, "missing: " + ", ".join(missing))


def install_stubs():
    global TEST_TMP
    TEST_TMP = Path(tempfile.mkdtemp(prefix="quizweb_test_"))
    quiz_game.base_dir = lambda: TEST_TMP
    quiz_game.require_agy = lambda: (object(), "")
    quiz_game.ask_quota = lambda agy: {"gemini_5h": 80}

    def fake_fetch(agy, cwd, theme, num, difficulty, verbose=False, on_retry=None):
        return make_questions(min(num, 3)), "テストテーマ"
    quiz_game.fetch_questions = fake_fetch


def req(method, url, token=None, body=None, host=None, origin=None, timeout=5):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    if token is not None:
        r.add_header("X-Quiz-Token", token)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    if host is not None:
        r.add_header("Host", host)
    if origin is not None:
        r.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def poll_status(base, token, want, timeout=8):
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        status, text = req("GET", base + "/api/status", token=token)
        if status == 200:
            last = json.loads(text)
            if last.get("state") == want:
                return last
            if want == "done" and last.get("state") == "error":
                return last
        time.sleep(0.1)
    return last


def stub_suite():
    check_dom_ids()
    install_stubs()
    httpd, token, port = quiz_web.create_server()
    base = "http://127.0.0.1:{}".format(port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    saved_files = []
    try:
        # --- static ---
        status, html = req("GET", base + "/")
        check("GET / 200", status == 200, str(status))
        check("indexにトークン埋込", token in html, "トークン未埋込")
        check("placeholder残存なし", quiz_web.TOKEN_PLACEHOLDER not in html)
        m = re.search(r'name="quiz-token" content="([^"]+)"', html)
        check("metaトークン一致", bool(m) and m.group(1) == token)

        for path, needle in (("/style.css", ".aurora"), ("/app.js", "confetti")):
            s, body = req("GET", base + path)
            check("GET {} 200".format(path), s == 200 and needle in body,
                  "status={} needle={}".format(s, needle in body))

        # --- host / token security ---
        s, _ = req("GET", base + "/api/config", token=token, host="evil.example")
        check("Host偽装 403", s == 403, str(s))

        s, _ = req("GET", base + "/api/config")
        check("トークンなし /api/config 403", s == 403, str(s))

        s, _ = req("GET", base + "/api/config", token="wrong-token")
        check("不正トークン 403", s == 403, str(s))

        s, _ = req("GET", base + "/api/status")
        check("status トークンなし 403", s == 403, str(s))

        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"num": 1, "difficulty": 1}, origin="http://evil.example")
        check("Origin偽装POST 403", s == 403, str(s))

        s, _ = req("POST", base + "/api/shutdown", body={})
        check("shutdown トークンなし 403", s == 403, str(s))

        # --- config ---
        s, body = req("GET", base + "/api/config", token=token)
        cfg = json.loads(body) if s == 200 else {}
        check("config 200", s == 200, str(s))
        check("難易度4段階", len(cfg.get("difficulties", [])) == 4, str(cfg.get("difficulties")))
        check("既定はcore由来",
              cfg.get("default_num") == quiz_game.DEFAULT_NUM
              and cfg.get("default_difficulty") == quiz_game.DEFAULT_DIFFICULTY)
        check("stop_thresholdはcore参照",
              cfg.get("stop_threshold") == quiz_game.QUOTA_STOP_THRESHOLD)

        # --- quota (stub) ---
        s, body = req("GET", base + "/api/quota", token=token)
        quota = json.loads(body) if s == 200 else {}
        check("quota 200/available", s == 200 and quota.get("gemini_5h") == 80, body[:120])

        # --- path traversal ---
        s, _ = req("GET", base + "/../../etc/passwd")
        check("トラバーサル 404", s == 404, str(s))

        # --- unknown api ---
        s, _ = req("GET", base + "/api/nope", token=token)
        check("未知API 404", s == 404, str(s))

        # --- questions job ---
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"theme": "テスト", "num": 3, "difficulty": 2})
        check("POST /api/questions 202", s == 202, str(s))
        job = poll_status(base, token, "done")
        ok_shape = (job.get("state") == "done" and len(job.get("questions", [])) == 3
                    and all(set(q) >= {"q", "choices", "answer", "explanation"}
                            for q in job["questions"]))
        check("出題ジョブ done/形状", ok_shape, json.dumps(job, ensure_ascii=False)[:200])
        check("meta/難易度名", job.get("meta") == "テストテーマ" and job.get("diff_name") == "ふつう")

        # --- save (reuses core.format_result_text) ---
        picks = [q["answer"] for q in job["questions"]]
        s, body = req("POST", base + "/api/save", token=token,
                      body={"score": len(picks), "picks": picks})
        save = json.loads(body) if s == 200 else {}
        path = Path(save.get("path", ""))
        ok_save = s == 200 and path.exists()
        if ok_save:
            saved_files.append(path)
            text = path.read_text(encoding="utf-8")
            ok_save = ("Q1:" in text and "解説:" in text
                       and "スコア: 3/3" in text)
        check("結果保存（core整形）", ok_save, body[:200])

        # --- comment calls core.comment_for ---
        calls = {"n": 0}
        original_comment = quiz_game.comment_for

        def counted(*a, **k):
            calls["n"] += 1
            return original_comment(*a, **k)
        quiz_game.comment_for = counted
        s, body = req("POST", base + "/api/comment", token=token,
                      body={"score": 3, "total": 3, "theme": "テストテーマ", "diff": "ふつう"})
        comment = json.loads(body).get("comment", "") if s == 200 else ""
        check("comment 200/core呼出", s == 200 and calls["n"] == 1 and bool(comment), body[:160])

        # --- invalid posts ---
        s, _ = req("POST", base + "/api/save", token=token, body={"score": 3, "picks": [0]})
        check("save 不正picks 400", s == 400, str(s))
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"num": 99, "difficulty": 1})
        check("questions 範囲外 400", s == 400, str(s))
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"num": 1, "difficulty": 1, "theme": "x" * 61})
        check("questions テーマ長 400", s == 400, str(s))
        s, _ = req("POST", base + "/api/comment", token=token,
                   body={"score": 9, "total": 3})
        check("comment 不正 400", s == 400, str(s))

        # --- cancel（世代ガード: 破棄→再開始可） ---
        def slow_fetch(agy, cwd, theme, num, difficulty, verbose=False, on_retry=None):
            time.sleep(1.0)
            return make_questions(1), "キャンセルテスト"
        quiz_game.fetch_questions = slow_fetch
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"theme": "", "num": 1, "difficulty": 1})
        check("cancel前 POST 202", s == 202, str(s))
        s, _ = req("POST", base + "/api/cancel", token=token, body={})
        check("cancel 200", s == 200, str(s))
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"theme": "", "num": 1, "difficulty": 1})
        check("cancel後 再開始可 202", s == 202, str(s))
        job = poll_status(base, token, "done")
        check("cancel後の新ジョブ done", job.get("state") == "done",
              json.dumps(job, ensure_ascii=False)[:160])

        # --- quota stop (stub 5%) ---
        quiz_game.ask_quota = lambda agy: {"gemini_5h": 5}
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"theme": "", "num": 1, "difficulty": 1})
        check("quota停止 POST 202", s == 202, str(s))
        job = poll_status(base, token, "error")
        check("quota停止をUIへ明示",
              job.get("state") == "error" and "停止" in job.get("error", ""),
              json.dumps(job, ensure_ascii=False)[:200])

        # --- shutdown ---
        s, _ = req("POST", base + "/api/shutdown", token=token, body={})
        check("shutdown 200", s == 200, str(s))
        time.sleep(0.4)
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
        for f in saved_files:
            try:
                f.unlink()
            except OSError:
                pass
        if TEST_TMP is not None:
            shutil.rmtree(TEST_TMP, ignore_errors=True)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("-" * 48)
    print("flow_test: {}/{} PASS".format(passed, total))
    if passed != total:
        print("FAIL詳細:")
        for name, ok, detail in RESULTS:
            if not ok:
                print("  - {} :: {}".format(name, detail))
        return 1
    return 0


def real_e2e():
    """実agyで出題経路を1回だけ確認する。残量が閾値以下なら停止する。"""
    httpd, token, port = quiz_web.create_server()
    base = "http://127.0.0.1:{}".format(port)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    saved = []
    try:
        s, body = req("GET", base + "/api/quota", token=token, timeout=100)
        quota = json.loads(body) if s == 200 else {}
        five = quota.get("gemini_5h")
        print("残量: {}".format(five))
        if five is not None and five <= quiz_game.QUOTA_STOP_THRESHOLD:
            check("quota作法により実askを停止", True, "残量{}%".format(five))
            return 0
        s, _ = req("POST", base + "/api/questions", token=token,
                   body={"theme": "", "num": 1, "difficulty": 1})
        check("実ask POST 202", s == 202, str(s))
        job = poll_status(base, token, "done", timeout=320)
        ok = (job.get("state") == "done" and len(job.get("questions", [])) == 1
              and all(set(q) >= {"q", "choices", "answer", "explanation"}
                      for q in job["questions"]))
        check("実ask done/形状", ok, json.dumps(job, ensure_ascii=False)[:300])
        if ok:
            q = job["questions"][0]
            print("  生成: {} | 選択肢{}件 | 正解{}".format(
                q["q"][:40], len(q["choices"]), q["answer"]))
            s, body = req("POST", base + "/api/save", token=token,
                          body={"score": 0, "picks": [0]})
            save = json.loads(body) if s == 200 else {}
            path = Path(save.get("path", ""))
            check("実結果保存", s == 200 and path.exists(), body[:160])
            if path.exists():
                saved.append(path)
        s, _ = req("POST", base + "/api/shutdown", token=token, body={})
        check("shutdown 200", s == 200, str(s))
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
        for f in saved:
            try:
                f.unlink()
            except OSError:
                pass
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("-" * 48)
    print("real_e2e: {}/{} PASS".format(passed, total))
    return 0 if passed == total else 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="quiz_web flow test")
    parser.add_argument("--real", action="store_true",
                        help="実agyで出題経路を1回確認（残量健全時のみ）")
    args = parser.parse_args(argv)
    return real_e2e() if args.real else stub_suite()


if __name__ == "__main__":
    sys.exit(main())
