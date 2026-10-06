"use strict";
(() => {
  const TOKEN = document.querySelector('meta[name="quiz-token"]').content;
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  };

  const state = {
    config: { difficulties: [], max_num: null, default_num: null, default_difficulty: null, stop_threshold: null },
    ready: false,
    theme: "",
    num: 5,
    difficulty: 2,
    questions: [],
    index: 0,
    score: 0,
    picks: [],
    answered: false,
    meta: "",
    diffName: "",
    timer: null,
  };

  async function api(path, opts = {}) {
    const headers = { "X-Quiz-Token": TOKEN };
    if (opts.body) headers["Content-Type"] = "application/json";
    const res = await fetch(path, {
      method: opts.method || "GET",
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    let data = {};
    try { data = await res.json(); } catch (_) { data = {}; }
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    return data;
  }

  let toastTimer = null;
  function toast(message) {
    const node = $("toast");
    node.textContent = message;
    node.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.remove("show"), 4200);
  }

  function show(screenId) {
    document.querySelectorAll(".screen").forEach((s) =>
      s.classList.toggle("active", s.id === screenId));
    const focusMap = { "screen-setup": "themeInput", "screen-quiz": "qText", "screen-result": "btnReplay" };
    const id = focusMap[screenId];
    if (id) {
      const node = $(id);
      if (node) {
        if (id === "qText") node.setAttribute("tabindex", "-1");
        node.focus({ preventScroll: true });
      }
    }
  }

  function diffName(value) {
    const hit = state.config.difficulties.find((d) => d.value === value);
    return hit ? hit.name : String(value);
  }

  // ---- setup ----
  function buildDifficulties(list, selected) {
    const group = $("diffGroup");
    group.replaceChildren();
    list.forEach((d) => {
      const b = el("button", "seg", d.name);
      b.type = "button";
      b.dataset.value = String(d.value);
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", String(d.value === selected));
      b.classList.toggle("on", d.value === selected);
      group.appendChild(b);
    });
  }

  function buildReplayDiff(list, selected) {
    const sel = $("replayDiff");
    sel.replaceChildren();
    list.forEach((d) => {
      const o = el("option", null, d.name);
      o.value = String(d.value);
      if (d.value === selected) o.selected = true;
      sel.appendChild(o);
    });
  }

  function setNum(value) {
    const max = state.config.max_num || 10;
    state.num = Math.max(1, Math.min(max, value));
    $("numValue").textContent = String(state.num);
  }

  function selectDifficulty(value, node) {
    state.difficulty = value;
    Array.from($("diffGroup").children).forEach((c) => {
      const on = c === node;
      c.classList.toggle("on", on);
      c.setAttribute("aria-checked", String(on));
    });
  }

  async function refreshQuota() {
    const badge = $("quotaBadge");
    badge.textContent = "残量 確認中…";
    badge.className = "badge";
    badge.removeAttribute("title");
    try {
      const q = await api("/api/quota");
      if (!q.available) {
        badge.textContent = "残量 取得不可";
        badge.classList.add("low");
        if (q.error) badge.title = q.error;
        return;
      }
      const five = q.gemini_5h;
      badge.textContent = "残量 " + five + "%";
      const low = state.config.stop_threshold != null && five <= state.config.stop_threshold;
      badge.classList.add(low ? "low" : "ok");
    } catch (e) {
      badge.textContent = "残量 取得不可";
      badge.classList.add("low");
    }
  }

  async function init() {
    bind();
    try {
      const cfg = await api("/api/config");
      state.config = Object.assign(state.config, cfg);
      state.difficulty = cfg.default_difficulty;
      buildDifficulties(cfg.difficulties, cfg.default_difficulty);
      buildReplayDiff(cfg.difficulties, cfg.default_difficulty);
      setNum(cfg.default_num);
      state.ready = true;
      $("btnStart").disabled = false;
      $("setupStatus").textContent = "準備完了。難易度はいつでも変更できます。";
    } catch (e) {
      state.ready = false;
      $("btnStart").disabled = true;
      $("setupStatus").textContent = "設定の取得に失敗しました。ページを再読み込みしてください。";
      toast("設定の取得に失敗: " + e.message);
    }
    refreshQuota();
  }

  // ---- generation ----
  function startQuiz(theme, num, difficulty) {
    if (!state.ready) { toast("設定を読み込めていません。再読み込みしてください。"); return; }
    $("btnStart").disabled = true;
    state.theme = theme;
    state.difficulty = difficulty;
    setNum(num);
    show("screen-loading");
    $("loadStatus").textContent = "出題を生成中…";
    $("loadMeta").textContent =
      (theme ? "「" + theme + "」" : "おまかせ") + " を " + state.num +
      "問（難易度: " + diffName(difficulty) + "）";
    $("loadElapsed").textContent = "0秒";
    $("loadEstimate").textContent = "—";
    $("loadRetry").hidden = true;
    api("/api/questions", { method: "POST", body: { theme, num: state.num, difficulty } })
      .then(() => poll())
      .catch((e) => {
        $("btnStart").disabled = false;
        toast("開始できません: " + e.message);
        show("screen-setup");
      });
  }

  function poll() {
    stopPoll();
    let fails = 0;
    state.timer = setInterval(async () => {
      let s;
      try { s = await api("/api/status"); fails = 0; }
      catch (e) {
        fails += 1;
        if (fails >= 6) {
          stopPoll();
          $("btnStart").disabled = false;
          toast("状態の取得に失敗しました。通信を確認してください。");
          show("screen-setup");
        }
        return;
      }
      $("loadElapsed").textContent = s.elapsed + "秒";
      $("loadEstimate").textContent = s.estimate ? s.estimate + "秒" : "—";
      $("loadRetry").hidden = !s.retrying;
      if (s.state === "done") { stopPoll(); beginQuiz(s); }
      else if (s.state === "error") {
        stopPoll();
        $("btnStart").disabled = false;
        toast(s.error || "出題の生成に失敗しました");
        show("screen-setup");
      }
    }, 500);
  }

  function stopPoll() {
    if (state.timer) { clearInterval(state.timer); state.timer = null; }
  }

  function beginQuiz(status) {
    state.questions = status.questions || [];
    state.meta = status.meta || "おまかせ";
    state.diffName = status.diff_name || diffName(state.difficulty);
    state.index = 0;
    state.score = 0;
    state.picks = [];
    $("btnStart").disabled = false;
    show("screen-quiz");
    renderQuestion();
  }

  // ---- quiz ----
  function renderQuestion() {
    const total = state.questions.length;
    const item = state.questions[state.index];
    state.answered = false;
    $("qIndex").textContent = "Q" + (state.index + 1) + "/" + total;
    $("qMeta").textContent = state.meta + " / 難易度: " + state.diffName;
    $("qProgressFill").style.width = (state.index / total) * 100 + "%";
    $("qText").textContent = item.q;
    $("feedback").textContent = "";
    $("feedback").className = "feedback";
    $("explainBox").hidden = true;
    $("explainText").textContent = "";
    $("scoreNow").textContent = "スコア " + state.score;
    const next = $("btnNext");
    next.disabled = true;
    next.textContent = state.index === total - 1 ? "結果を見る" : "次の問題へ";

    const box = $("choices");
    box.replaceChildren();
    item.choices.forEach((text, i) => {
      const b = el("button", "choice");
      b.type = "button";
      b.style.animationDelay = (i * 60) + "ms";
      b.appendChild(el("span", "key", String(i + 1)));
      b.appendChild(el("span", "label", text));
      b.addEventListener("click", () => answer(i));
      box.appendChild(b);
    });
  }

  function answer(picked) {
    if (state.answered) return;
    state.answered = true;
    state.picks.push(picked);
    const item = state.questions[state.index];
    const buttons = Array.from($("choices").children);
    buttons.forEach((b, i) => {
      b.disabled = true;
      if (i === item.answer) b.classList.add("correct");
      else if (i === picked) b.classList.add("wrong");
      else b.classList.add("dim");
    });
    const fb = $("feedback");
    if (picked === item.answer) {
      state.score += 1;
      fb.textContent = "正解";
      fb.className = "feedback good";
    } else {
      fb.textContent = "不正解。正解は " + (item.answer + 1) + " です。";
      fb.className = "feedback bad";
    }
    $("explainText").textContent = item.explanation || "解説なし";
    $("explainBox").hidden = false;
    $("scoreNow").textContent = "スコア " + state.score;
    $("btnNext").disabled = false;
  }

  function next() {
    if (state.index + 1 >= state.questions.length) finish();
    else { state.index += 1; renderQuestion(); }
  }

  // ---- result ----
  function finish() {
    const total = state.questions.length;
    const score = state.score;
    const rate = total ? score / total : 0;
    show("screen-result");
    $("resultScore").textContent = score + "/" + total;
    $("resultRate").textContent = Math.round(rate * 100) + "%";
    const ring = $("ringFg");
    ring.style.stroke = rate >= 0.8 ? "var(--good)" : rate >= 0.5 ? "var(--accent)" : "var(--bad)";
    ring.style.strokeDashoffset = String(326.7 * (1 - rate));
    $("savedPath").textContent = "";
    const sel = $("replayDiff");
    const current = state.config.difficulties.find((d) => d.value === state.difficulty);
    if (current) sel.value = String(current.value);
    api("/api/comment", {
      method: "POST",
      body: { score, total, theme: state.meta, diff: state.diffName },
    }).then((d) => { $("resultComment").textContent = d.comment; })
      .catch(() => { $("resultComment").textContent = "結果: " + score + "/" + total; });
    if (rate >= 0.8) confetti();
  }

  async function saveResult() {
    try {
      const d = await api("/api/save", {
        method: "POST",
        body: { score: state.score, picks: state.picks },
      });
      $("savedPath").textContent = "保存しました: " + d.path;
    } catch (e) {
      toast("保存できません: " + e.message);
    }
  }

  function replay() {
    const value = parseInt($("replayDiff").value, 10);
    startQuiz(state.theme, state.num, value);
  }

  async function quit() {
    try { await api("/api/shutdown", { method: "POST", body: {} }); } catch (_) { /* noop */ }
    toast("終了しました。タブを閉じてください。");
  }

  async function cancelLoad() {
    stopPoll();
    try { await api("/api/cancel", { method: "POST", body: {} }); } catch (_) { /* noop */ }
    $("btnStart").disabled = false;
    toast("生成をやめました（実行中の生成は破棄されます）");
    show("screen-setup");
  }

  // ---- fx ----
  function confetti() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = $("fx");
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + "px";
    canvas.style.height = innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const colors = ["#7c8cff", "#c084fc", "#22d3ee", "#34d399", "#fbbf24", "#fb7185"];
    const parts = [];
    for (let i = 0; i < 140; i++) {
      parts.push({
        x: Math.random() * innerWidth,
        y: -20 - Math.random() * innerHeight * 0.4,
        vx: (Math.random() - 0.5) * 2.4,
        vy: 2 + Math.random() * 4,
        s: 5 + Math.random() * 7,
        r: Math.random() * Math.PI,
        vr: (Math.random() - 0.5) * 0.3,
        color: colors[i % colors.length],
      });
    }
    const start = performance.now();
    const life = 3200;
    (function frame(now) {
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      const alpha = Math.max(0, 1 - (now - start) / life);
      parts.forEach((p) => {
        p.x += p.vx; p.y += p.vy; p.r += p.vr; p.vy += 0.05;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.r);
        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 0.6);
        ctx.restore();
      });
      if (now - start < life) requestAnimationFrame(frame);
      else ctx.clearRect(0, 0, innerWidth, innerHeight);
    })(start);
  }

  // ---- bindings ----
  function bind() {
    $("btnStart").addEventListener("click", () =>
      startQuiz($("themeInput").value.trim(), state.num, state.difficulty));
    $("btnNumMinus").addEventListener("click", () => setNum(state.num - 1));
    $("btnNumPlus").addEventListener("click", () => setNum(state.num + 1));
    $("diffGroup").addEventListener("click", (ev) => {
      const b = ev.target.closest(".seg");
      if (!b) return;
      selectDifficulty(parseInt(b.dataset.value, 10), b);
    });
    $("diffGroup").addEventListener("keydown", (ev) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(ev.key)) return;
      ev.preventDefault();
      const items = Array.from($("diffGroup").children);
      const cur = items.findIndex((c) => c.classList.contains("on"));
      const dir = (ev.key === "ArrowRight" || ev.key === "ArrowDown") ? 1 : -1;
      const nxt = (cur + dir + items.length) % items.length;
      items[nxt].click();
      items[nxt].focus();
    });
    $("btnNext").addEventListener("click", next);
    $("btnSave").addEventListener("click", saveResult);
    $("btnReplay").addEventListener("click", replay);
    $("btnBackSetup").addEventListener("click", () => { refreshQuota(); show("screen-setup"); });
    $("btnCancelLoad").addEventListener("click", cancelLoad);
    $("btnQuit").addEventListener("click", quit);
    $("btnQuitQuiz").addEventListener("click", quit);
    window.addEventListener("pagehide", stopPoll);
    document.addEventListener("keydown", (ev) => {
      if (!$("screen-quiz").classList.contains("active")) return;
      if (ev.key >= "1" && ev.key <= "4") {
        answer(parseInt(ev.key, 10) - 1);
      } else if (ev.key === "Enter" && !$("btnNext").disabled) {
        next();
      }
    });
  }

  init();
})();
