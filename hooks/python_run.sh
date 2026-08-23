#!/usr/bin/env bash
# Pythonインタプリタを判定してスクリプトを実行する共通ヘルパー
# WindowsのApp Storeエイリアス（スタブ）やインタプリタ欠落を回避する
# 探索順: python3（Linux/macOS）→ python（Windows実装）→ py -3（Windows pyランチャー）
# 使い方: bash "$(dirname "$0")/python_run.sh" <script.py> [args...]
for PY in python3 python "py -3"; do
    # shellcheck disable=SC2086
    if $PY -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" >/dev/null 2>&1; then
        # shellcheck disable=SC2086
        exec $PY "$@"
    fi
done
echo "ERROR: Python interpreter not found (tried python3, python, py -3)" >&2
exit 1
