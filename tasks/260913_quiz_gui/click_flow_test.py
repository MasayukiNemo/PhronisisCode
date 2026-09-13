#!/usr/bin/env python3
"""click_flow_test.py — GUIクリック完走のヘッドレス検証（stubs＋invoke）。

出題・quotaを差し替えて全画面遷移を回す。ネットワーク・quotaを消費しない。
成功時は flow-ok を出して exit 0。
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

import tkinter as tk

import quiz_game
import quiz_gui

quiz_game.ask_quota = lambda agy: {"gemini_5h": 100}


def _stub_fetch(agy, cwd, theme, num, d, on_progress=None):
    if on_progress:
        on_progress(1, 1, True)
    return ([{"q": "Q?", "choices": ["a", "b", "c", "d"],
              "answer": 1, "explanation": "E!"}],
            "T/" + quiz_game.DIFFICULTY[d][0])


quiz_game.fetch_questions = _stub_fetch


def pump(root, cond, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        root.update()
        if cond():
            return True
        time.sleep(0.05)
    return False


def main():
    root = tk.Tk()
    app = quiz_gui.QuizApp(root)
    root.update()
    app._on_start()
    assert pump(root, lambda: len(app.answer_buttons) == 4), "no-questions"
    assert getattr(app, "progress_done", 0) == 1, "no-counter"
    app.answer_buttons[3].invoke()
    root.update()
    assert app.feedback_var.get().startswith("不正解"), app.feedback_var.get()
    assert "解説" in app.explain_var.get(), app.explain_var.get()
    assert app.next_btn.instate(["!disabled"]), "next-locked"
    assert app.next_btn.cget("text") == "結果を見る", app.next_btn.cget("text")
    app.next_btn.invoke()
    root.update()
    replay = [w for w in root.winfo_children()[0].winfo_children()
              if w.winfo_class() == "TFrame"]
    buttons = []
    for fr in replay:
        buttons += [w for w in fr.winfo_children()
                    if w.winfo_class() == "TButton"]
    again = [w for w in buttons if w.cget("text") == "同じテーマで別セット"]
    assert again, "no-replay"
    again[0].invoke()
    root.update()
    assert pump(root, lambda: len(app.answer_buttons) == 4
                and app.index == 0), "no-replay-questions"
    app.answer_buttons[1].invoke()
    root.update()
    assert app.feedback_var.get().startswith("正解"), app.feedback_var.get()
    app.next_btn.invoke()
    root.update()
    back = [w for w in root.winfo_children()[0].winfo_children()
            if w.winfo_class() == "TButton" and w.cget("text") == "設定に戻る"]
    assert back, "no-back"
    save = [w for w in root.winfo_children()[0].winfo_children()
            if w.winfo_class() == "TButton" and w.cget("text") == "結果を保存"]
    assert save, "no-save"
    save[0].invoke()
    root.update()
    saved = None
    for w in root.winfo_children()[0].winfo_children():
        if w.winfo_class() == "TLabel" and w.cget("text").startswith(
                "保存しました"):
            saved = w.cget("text").split(": ", 1)[1]
    assert saved, "no-saved-path"
    from pathlib import Path as _P
    assert _P(saved).exists(), saved
    body = _P(saved).read_text(encoding="utf-8")
    assert "Q1" in body and "解説" in body, body[:200]
    _P(saved).unlink()
    back[0].invoke()
    root.update()
    assert hasattr(app, "start_btn"), "no-setup-return"
    print("flow-ok: 不正解→解説→結果→別セット→正解→結果→設定")
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
