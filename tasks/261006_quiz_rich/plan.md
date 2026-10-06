# plan.md — クイズ リッチWeb UI版 実装計画

## アーキテクチャ

```
[Browser: 127.0.0.1:port]  index.html + style.css + app.js
        │  fetch(API, X-Quiz-Token)
        ▼
[Python: scripts/quiz_web.py]  ThreadingHTTPServer（127.0.0.1限定）
   - GET  /            → quiz_webui/index.html（トークン埋込）
   - GET  /style.css   → 静的
   - GET  /app.js      → 静的（トークンをmetaから読む）
   - GET  /api/quota   → core.require_agy / core.ask_quota
   - POST /api/questions → quota確認→core.fetch_questions（唯一の出題経路）
   - POST /api/shutdown  → サーバ停止（UIの「終了」導線）
        │
        ▼
[core: scripts/quiz_game.py]  出題ロジックの単一正本（再利用。複写しない）
```

- 出題・救済・検証・難易度・quotaはすべて core 側。quiz_web.py は薄いHTTPアダプタに徹する
- 静的資産は quiz_webui/ に分離。CDN・Webフォント不使用でオフライン動作
- セキュリティ: 起動時にワンタイムトークン生成→index.htmlに埋込→APIはヘッダ照合。
  Host/Originを127.0.0.1/localhostに検証。本文サイズ上限を設ける

## タスク分解

1. [ ] brief / deep_thought / plan 作成（課題確定）
2. [ ] トライアングル（Yuna / Hayato / Gaia / Artemis）→ 統合
3. [ ] scripts/quiz_web.py 実装（サーバ・API・トークン・quota・静的配信・ブラウザ起動）
4. [ ] scripts/quiz_webui/index.html 実装（画面構造）
5. [ ] scripts/quiz_webui/style.css 実装（リッチ表現・アニメ・レスポンシブ）
6. [ ] scripts/quiz_webui/app.js 実装（状態機械・API・DOM・結果保存）
7. [ ] flow_test（stubで全遷移検証、quota消費なし）
8. [ ] Metisレビュー → 反映
9. [ ] Hayatoゲート（4点）→ 確定
10. [ ] commit / push

## 依存関係

```
brief → トライアングル → quiz_web.py → webui(index/style/app) → flow_test → Metis → Hayato → 確定
```

## リスク

- リスク1: ブラウザ自動オープン失敗 → webbrowser例外を握り、URLを必ずコンソール表示
- リスク2: ポート衝突 → port=0 で空きポートをOSに割当てさせ取得
- リスク3: 生成中の二重送信 → 起動ボタンdisable＋サーバ側で処理中フラグ
- リスク4: XSS（LLM出力をDOMへ） → textContentのみ。innerHTMLは静的雛形以外禁止
- リスク5: プロセス残留 → /api/shutdown＋Ctrl+C＋daemonスレッド
- リスク6: 検証で実agyを叩く → stubに差替えたflow_testで検証（quota消費ゼロ）

<!-- status: complete | agent: kai -->
