#!/usr/bin/env python3
"""
quiz_gui.py — Geminiおまかせクイズゲーム（GUI版）

マウス主導で遊べるtkinter版（テーマ入力のみキーボード）。
出題ロジックは quiz_game.py の純粋関数を再利用する（二重実装しない）。
conduct準拠: ask前にquota確認、7%以下は停止。

完走シナリオ: 設定→開始→回答クリック→次へ→結果→もう一度
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tkinter as tk
from tkinter import messagebox, ttk

import quiz_game as core

QUOTA_STOP_THRESHOLD = 7


class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Geminiクイズ")
        self.root.geometry("720x720")
        self.root.minsize(600, 600)
        style = ttk.Style()
        for name in ("clam", "vista", "winnative"):
            if name in style.theme_names():
                style.theme_use(name)
                break
        style.configure("TButton", padding=6, font=("", 11))
        style.configure("Title.TLabel", font=("", 18, "bold"))
        style.configure("Q.TLabel", font=("", 13, "bold"))
        self.agy = None
        self.cwd = core.base_dir()
        self.questions = []
        self.index = 0
        self.score = 0
        self.epoch = 0
        self._holder = (0, "", None)
        self.answer_buttons = []
        self._build_setup()

    # -- 画面共通 --
    def _clear(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.answer_buttons = []

    def _fail(self, title, message):
        messagebox.showerror(title, message)

    # -- 設定画面 --
    def _build_setup(self):
        self._clear()
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Geminiクイズ",
                  style="Title.TLabel").pack(pady=(0, 12))

        ttk.Label(frame, text="テーマ（空でおまかせ）:").pack(anchor=tk.W)
        self.theme_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.theme_var, width=50).pack(
            anchor=tk.W, pady=(0, 8))

        row = ttk.Frame(frame)
        row.pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(row, text="設問数:").pack(side=tk.LEFT)
        self.num_var = tk.StringVar(value="5")
        ttk.Combobox(row, textvariable=self.num_var, width=5,
                     state="readonly",
                     values=[str(n) for n in range(1, 11)]).pack(
            side=tk.LEFT, padx=(4, 16))
        ttk.Label(row, text="難易度:").pack(side=tk.LEFT)
        self.diff_label = tk.StringVar(value=core.DIFFICULTY[2][0])
        self.diff_box = ttk.Combobox(
            row, textvariable=self.diff_label, width=12, state="readonly",
            values=[v[0] for _, v in sorted(core.DIFFICULTY.items())])
        self.diff_box.current(1)
        self.diff_box.pack(side=tk.LEFT, padx=4)

        self.start_btn = ttk.Button(frame, text="開始", command=self._on_start)
        self.start_btn.pack(pady=12)
        self.status_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_var,
                  foreground="gray").pack(anchor=tk.W)

    def _on_start(self):
        self.start_btn.state(["disabled"])
        try:
            num = int(self.num_var.get())
        except ValueError:
            num = 5
        num = min(max(num, 1), 10)
        name = self.diff_label.get()
        difficulty = next((k for k, v in core.DIFFICULTY.items() if v[0] == name), 2)
        theme = self.theme_var.get().strip()
        self.last_theme = theme
        self.last_num = num
        self.last_diff = difficulty
        self.status_var.set("準備中…")
        epoch = self.epoch + 1
        self.epoch = epoch
        self._holder = (epoch, "", None)
        self.retrying = False
        thread = threading.Thread(
            target=self._generate,
            args=(theme, num, difficulty, epoch), daemon=True)
        thread.start()
        self._build_loading(epoch, self._loading_text(theme, num, difficulty))

    @staticmethod
    def _loading_text(theme, num, difficulty):
        name = core.DIFFICULTY[difficulty][0]
        shown = theme if theme else "おまかせ"
        return "「{}」を{}問生成中…（難易度:{}、目安最大{}秒）".format(
            shown, num, name, core.timeout_for(num))

    # -- 生成中画面 --
    def _build_loading(self, epoch, status="出題を生成中…"):
        self._clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=tk.BOTH, expand=True)
        self.load_base = status
        self.load_status_var = tk.StringVar(value=status)
        ttk.Label(frame, textvariable=self.load_status_var,
                  font=("", 14), wraplength=600).pack(pady=(40, 12))
        self.elapsed_var = tk.StringVar(value="経過0秒")
        ttk.Label(frame, textvariable=self.elapsed_var,
                  foreground="gray").pack()
        self._loading_since = time.time()
        self._tick(epoch)
        bar = ttk.Progressbar(frame, mode="indeterminate", length=320)
        bar.pack()
        bar.start(15)
        ttk.Button(frame, text="やめる",
                   command=lambda: self._cancel_to_setup(epoch)).pack(pady=16)
        self.root.after(200, lambda: self._poll_result(epoch))

    def _tick(self, epoch):
        if epoch != self.epoch:
            return
        try:
            self.elapsed_var.set("経過{}秒".format(
                int(time.time() - self._loading_since)))
            base = self.load_base
            if getattr(self, "retrying", False):
                base += "（再試行中）"
            self.load_status_var.set(base)
        except tk.TclError:
            return
        self.root.after(1000, lambda: self._tick(epoch))

    def _cancel_to_setup(self, epoch):
        self.epoch = epoch + 1
        self._holder = (self.epoch, "", None)
        self._build_setup()

    def _generate(self, theme, num, difficulty, epoch):
        """別スレッドでquota→出題。結果も例外もholderに格納する。"""
        try:
            agy, err = core.require_agy()
            if agy is None:
                self._holder = (epoch, "error", "開始できません: {}".format(err))
                return
            quota = core.ask_quota(agy)
            five = quota.get("gemini_5h")
            if five is not None and five <= QUOTA_STOP_THRESHOLD:
                self._holder = (
                    epoch, "error",
                    "残量{}%のため開始しません（7%以下は停止）。".format(five))
                return
            questions, meta = core.fetch_questions(
                agy, self.cwd, theme, num, difficulty,
                on_retry=self._mark_retry)
            if not questions:
                self._holder = (
                    epoch, "error", "出題の生成に失敗: {}".format(meta))
                return
            self._holder = (
                epoch, "ok",
                (agy, questions, meta,
                 core.DIFFICULTY[difficulty][0]))
        except Exception as exc:
            self._holder = (epoch, "error", "生成中に失敗: {}".format(exc))

    def _poll_result(self, epoch):
        if epoch != self.epoch:
            return
        holder_epoch, kind, payload = self._holder
        if holder_epoch != epoch or kind == "":
            self.root.after(200, lambda: self._poll_result(epoch))
            return
        self._holder = (epoch, "", None)
        if kind == "error":
            self._fail("出題失敗", payload)
            self._build_setup()
            return
        self.agy, self.questions, meta, diff_name = payload
        self.index = 0
        self.score = 0
        self.picks = []
        self.theme_name = meta
        self.diff_name = diff_name
        self.meta_line = "{} / 難易度: {}".format(meta, diff_name)
        self._build_question()

    # -- 出題画面 --
    def _build_question(self):
        self._clear()
        self.answered = False
        item = self.questions[self.index]
        total = len(self.questions)
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(frame)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Q{}/{}  {}".format(
            self.index + 1, total, self.meta_line),
            foreground="gray").pack(side=tk.LEFT)
        ttk.Button(top, text="やめる",
                   command=lambda: self._cancel_to_setup(self.epoch)).pack(
            side=tk.RIGHT)

        ttk.Label(frame, text=item["q"], style="Q.TLabel",
                  wraplength=660, justify=tk.LEFT).pack(
            anchor=tk.W, pady=(8, 12))

        for n, choice in enumerate(item["choices"]):
            btn = tk.Button(frame, text="{}. {}".format(n + 1, choice),
                            anchor="w", justify="left", wraplength=620,
                            font=("", 11), padx=8, pady=6,
                            command=lambda p=n: self._answer(p))
            btn.pack(fill=tk.X, pady=3)
            self.answer_buttons.append(btn)

        self.feedback_var = tk.StringVar()
        self.explain_var = tk.StringVar(value="回答すると解説がここに出ます")
        self.feedback_label = ttk.Label(
            frame, textvariable=self.feedback_var, font=("", 12, "bold"),
            wraplength=620, justify=tk.LEFT)
        self.feedback_label.pack(anchor=tk.W, pady=(8, 4))
        box = ttk.Frame(frame, relief="sunken", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(box, textvariable=self.explain_var,
                  wraplength=640, justify=tk.LEFT).pack(
            anchor=tk.W)
        nav = ttk.Frame(frame)
        nav.pack(fill=tk.X)
        last = self.index == len(self.questions) - 1
        self.next_btn = ttk.Button(nav,
                                   text="結果を見る" if last else "次の問題へ",
                                   command=self._next, state="disabled")
        self.next_btn.pack(side=tk.RIGHT)
        self.score_var = tk.StringVar(
            value="スコア: {}".format(self.score))
        ttk.Label(frame, textvariable=self.score_var,
                  foreground="gray").pack(anchor=tk.E)

    def _answer(self, picked):
        if self.answered:
            return
        self.answered = True
        self.picks.append(picked)
        item = self.questions[self.index]
        for n, btn in enumerate(self.answer_buttons):
            btn.configure(state="disabled")
            if n == item["answer"]:
                btn.configure(text=btn.cget("text") + "  ○")
        if picked == item["answer"]:
            self.score += 1
            self.feedback_var.set("正解")
            self.feedback_label.configure(foreground="green")
        else:
            self.feedback_var.set(
                "不正解。正解は {} です。".format(item["answer"] + 1))
            self.feedback_label.configure(foreground="red")
        if item["explanation"]:
            self.explain_var.set("解説: {}".format(item["explanation"]))
        else:
            self.explain_var.set("解説なし")
        self.score_var.set("スコア: {}".format(self.score))
        self.next_btn.state(["!disabled"])

    def _save_result(self):
        """出題・回答・正解・解説をテキスト保存する。戻り: 保存パス。"""
        import datetime
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.cwd / "quiz_{}.txt".format(stamp)
        lines = [
            "Geminiクイズ結果 {}".format(
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
            "テーマ: {} / 難易度: {} / スコア: {}/{}".format(
                self.theme_name, self.diff_name, self.score,
                len(self.questions)),
            "",
        ]
        for i, (item, picked) in enumerate(
                zip(self.questions, self.picks), 1):
            mark = "正解" if picked == item["answer"] else "不正解"
            lines.append("Q{}: {}".format(i, item["q"]))
            for n, choice in enumerate(item["choices"], 1):
                lines.append("  {}. {}".format(n, choice))
            lines.append("  回答: {} / 正解: {} → {}".format(
                picked + 1, item["answer"] + 1, mark))
            if item["explanation"]:
                lines.append("  解説: {}".format(item["explanation"]))
            lines.append("")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
        except OSError as exc:
            self._fail("保存失敗", "保存できません: {}".format(exc))
            return None
        self.saved_var.set("保存しました: {}".format(path))
        return path

    def _mark_retry(self):
        self.retrying = True

    def _replay(self):
        """同じテーマ・設問数で別セットを生成する。難易度は選択値を使う。"""
        name = self.retry_diff.get()
        difficulty = next(
            (k for k, v in core.DIFFICULTY.items() if v[0] == name),
            self.last_diff)
        self.last_diff = difficulty
        epoch = self.epoch + 1
        self.epoch = epoch
        self._holder = (epoch, "", None)
        self.retrying = False
        thread = threading.Thread(
            target=self._generate,
            args=(self.last_theme, self.last_num, difficulty, epoch),
            daemon=True)
        thread.start()
        self._build_loading(
            epoch,
            self._loading_text(self.last_theme, self.last_num, difficulty))

    def _next(self):
        self.index += 1
        if self.index >= len(self.questions):
            self._build_result()
        else:
            self._build_question()

    # -- 結果画面 --
    def _build_result(self):
        self._clear()
        total = len(self.questions)
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="結果",
                  font=("", 20, "bold")).pack(pady=(40, 8))
        ttk.Label(frame, text=core.comment_for(
            self.score, total, self.theme_name, self.diff_name),
            font=("", 12), wraplength=600).pack(pady=(0, 16))
        row = ttk.Frame(frame)
        row.pack(pady=(0, 12))
        ttk.Label(row, text="難易度:").pack(side=tk.LEFT)
        self.retry_diff = tk.StringVar(value=self.diff_name)
        ttk.Combobox(row, textvariable=self.retry_diff, width=12,
                     state="readonly",
                     values=[v[0] for _, v in sorted(
                         core.DIFFICULTY.items())]).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="同じテーマで別セット",
                   command=self._replay).pack(side=tk.LEFT, padx=(8, 0))
        self.saved_var = tk.StringVar()
        ttk.Button(frame, text="結果を保存",
                   command=self._save_result).pack(pady=(4, 0))
        ttk.Label(frame, textvariable=self.saved_var,
                  foreground="gray", wraplength=600).pack()
        ttk.Button(frame, text="設定に戻る",
                   command=self._build_setup).pack(pady=(8, 0))


def main():
    root = tk.Tk()
    QuizApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
