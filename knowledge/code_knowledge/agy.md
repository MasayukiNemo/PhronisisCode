# agy 外部AI（Code限定運用）

出典: 本家 PhronisisCore commit db1a221 の agy_external_ai.md / agy_query.py をCode向けに絞って記録。正本は scripts/agy_query.py（Code適応版）。

## Codeで使うもの

- quota: `python scripts/agy_query.py quota` → 残量JSON。使う前に残量確認
- ask: `python scripts/agy_query.py ask "質問"` → Coding補助の第二意見・詰まり時の壁打ち。外部由来の非信頼文をプロンプトに混ぜない
- generate: `python scripts/agy_query.py generate "指示" --out <path>` → アイコン等素材。会話継続は `--conversation <ID>`。実測は任意。--outはリポジトリ内に限定する

## Codeで使わないもの

- extract / multimodal_ingest: 画像/PDF下処理の需要が薄いため不使用。コードと--helpには温存されるが呼ばない。誤って叩いた場合はCode運用外として結果を利用しない
- --auto-model / APIフォールバック: Codeはagy-only。7%以下は使わない（askは残量を見ずHighに突っ込むため手動停止、generateはMedium継続するため手動停止）。黙ってAPI課金に落ちない
- MarkItDown等の追加依存: なし（標準ライブラリのみ維持）

## 罠（本家実測より、Codeでも有効）

- 生成物はagyのscratchに置かれる。ブリッジのコピー処理に依存する
- agyは兄弟ディレクトリまで探索しうる。cwd絞り＋リポジトリ外拒否はあるが完全サンドボックスではない
- narration（短い進捗返答）は1回リトライのみ。別表現はすり抜けうる
- 文字化け検出はヒューリスティック。コンソール表示の化けと成果物の化けは別物で、確認はReadツールで行う
- --dangerously-skip-permissionsで動くため、リポジトリ内ファイル（.env等）も技術的には読み取り可能。プロンプト制限に強制力なし。残存リスクとして認識する
- モデル名は更新される。`agy models` で確認する

## 導入・認証（人間が1回）

- Windows: `irm https://antigravity.google/cli/install.ps1 | iex` → `%LOCALAPPDATA%\agy\bin\agy.exe`
- 認証: `agy` を対話起動してGoogleログイン。以降ヘッドレスで再利用
- 検証: quota → 残量%、ask一言 → 応答
