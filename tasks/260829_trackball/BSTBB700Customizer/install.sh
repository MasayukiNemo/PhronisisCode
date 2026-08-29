#!/bin/bash
# BSTBB700Customizer 友人向けインストーラ（ad-hoc署名用・操作3ステップに簡略化）
# 使い方: zipを展開して ./install.sh をダブルクリック or ターミナルで実行
set -e
APP_SRC="$(cd "$(dirname "$0")" && pwd)/BSTBB700Customizer.app"
APP_DST="/Applications/BSTBB700Customizer.app"

echo "==> BSTBB700Customizer インストール開始"

if [ ! -d "$APP_SRC" ]; then
  echo "エラー: BSTBB700Customizer.app が見つかりません。zipを正しく展開してください。"
  exit 1
fi

echo "1/3 アプリを /Applications にコピー..."
rm -rf "$APP_DST"
cp -R "$APP_SRC" "$APP_DST"

echo "2/3 Gatekeeper回避 (xattr -cr)..."
xattr -cr "$APP_DST" 2>/dev/null || true

echo "3/3 アプリを起動..."
open "$APP_DST" || true
sleep 1
echo "   入力監視の設定画面を開きます..."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_InputMonitoring" || true
sleep 1
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" || true

cat << 'MSG'

完了しました。

次の2つをONにしてください:
  システム設定 > プライバシーとセキュリティ > 入力監視 > BSTBB700Customizer をON
  システム設定 > プライバシーとセキュリティ > アクセシビリティ > BSTBB700Customizer をON

一覧にない場合は「+」で /Applications/BSTBB700Customizer.app を追加してください。
ONにした後は、このターミナルで表示された BSTBB700Customizer のウィンドウで
「再チェック」を押すか、アプリを再起動してください。

※ 初回のみこの操作が必要です。アップデート時は同じ手順で上書きしてください。
MSG
