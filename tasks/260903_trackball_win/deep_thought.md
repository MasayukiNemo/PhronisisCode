# deep_thought.md — Kai 深層思考

## 課題の本質

表層は「Windows版ボタン割り当てアプリ」だが、本質はMac版で払った授業料の移植である。Mac版の核心は「EventTapのdeltaは無視され、Warpは縮小時逆走するため、HID加速テーブルの一時変更だけが確実」という到達点だ。Windowsでも同じ罠（フックでdeltaをいじる、低レベルでカーソル位置を打ち直す）に落ちないことが最優先である。

根本さんの判断OSに照らす:
- 苦労は逃げろ: Raw Inputの完全分離やドライバに手を出さない。WH_MOUSE_LLフックとSystemParametersInfoで逃げる
- 選ぶことは捨てること: 今回捨てるものは a) デバイス限定減速の即時達成（MVPはグローバルで明記） b) C#ネイティブ化（Pythonでまず動かす） c) チルトのホールド対応（upがないためトグルのみ）
- ユカイじゃない検出器: 割り当てたのに効かない、精密で逆に動く、ホールドが一瞬で切れる、の3点はMac版で実証済みのユカイじゃない。WinではXBUTTONのdown/upで2つ目と3つ目を潰せる

## 構造把握

レイヤ:
1. 取得層: WH_MOUSE_LL（XBUTTON1/2、MBUTTON、HWHEEL）+ WH_KEYBOARD_LL（F13等トリガー用）
2. 変換層: ButtonID→KeyCombo、チルトH判定、未割り当て素通し/割り当て時横取り
3. 精密層: SystemParametersInfoでSPI_GETMOUSESPEED保存→SPI_SETMOUSESPEEDにscale反映→OFFで復元。トグル/ホールド状態管理
4. 設定層: JSONファイル、排他バリデーション
5. UI層: タスクトレイ + tkinter設定 + 精密ON表示

リスクの構造:
- 最大リスクはMacのコンテクストをWinに誤写像すること。MacのCtrl+→エミュレーションはWinでは起きない。逆にWinのXBUTTONはMacのotherMouseDownと挙動が違う。差分を明確にする
- 次に権限: 管理者不要だが、低レベルフックはウイルス対策に誤検知される可能性。署名なしMVPはSmartScreen警告が出る。zip配布で手順を明記する
- 精密の復元漏れ: クラッシュ時に低速が残留する。atexit/signalと設定保存で二重復元する（Mac版SystemPointerSpeedと同対策）

## 確信度

- 技術方針 80%（Win32 APIは公開仕様で安定。Mac版の失敗知見でWarp/deltaを捨てる判断は堅い）
- 要件確信度 75%（Mac版の5入力と精密択一を踏襲。Win固有の進むホールド可は根本さんの指示で確定）

## 次のアクション

- Yunaに「MacのBとWinのBのズレ」を照合させ、Hayatoに「Macの決め打ちをWinに持ち込む矛盾」を刺させる。その後実装に入る。
