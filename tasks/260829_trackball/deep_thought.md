# deep_thought.md — Kai 深層思考

## 課題の本質

表層は「トラックボールのボタン割り当てアプリ」だが、本質は macOSのHIDイベント横取りと権限の戦い。根本さんが求めているのは「細かい操作のための精密モード」＋「チルト/進む戻るの自由化」。特に精密モードは既存の市販ドライバ（SteerMouse等）でも不完全な領域で、差別化の核になる。

根本さんの判断OSに照らす:
- 本質抽出・概念優先: 「カーソル速度を落とす」は単なるスケールではなく「人間の微細運動を支援する」概念。トグル/ホールドの両立は「選ぶことは捨てること」に反するように見えるが、ここは両方を残すことでユーザの身体性（押しながら精密作業 vs モード切替で長時間精密作業）の違いを吸収する。正当な両立。
- 即断即決: 技術方式はCGEventTap一択。迷わない。kextやDriverKitは過剰。
- 追従性: 設定UIは人間が把握可能な範囲に留める。プロファイル分岐やアプリ別設定は任意に格下げ。

## 構造把握

レイヤ:
1. HID取得層: IOHIDManagerでBluetoothトラックボールを識別、またはCGEventTap(type .otherMouseDown/Up, scrollWheel)で横取り
2. 変換層: ボタンID→キーコンボマッピング、ホイールチルト→キーコンボ/水平スクロール抑止
3. 精密モード層: CGEvent mouseMoved/mouseDragged の deltaX/deltaY を係数kでスケール。トグル状態管理とホールド状態管理を分離
4. 設定層: UserDefaults+JSON、ホットキー登録 (Carbon RegisterEventHotKey or NSEvent globalMonitor)
5. UI層: MenuBarExtra + Settings Window, TCC権限ガイド

リスクの構造:
- 最大リスクは「進む戻るがキーボードエミュレーションである」こと。CGEventTapで見ると .keyDown として届く可能性があり、ボタン由来とキーボード由来の区別がつかない。IOHIDレベルで見ればボタンとして区別可能だが、CGEventレベルでは区別不能。検証が必要。
- 次にTCC: Input Monitoringがなければtapが無効化される。初回起動時のガイドがUXを決める。
- 精密モードの係数適用時にscrollWheelやtrackpadまで巻き込まないよう、sourceフィルタが必須。

## 判断OSへの照合（conductor_profile_lite.md）

- 「苦労は逃げろ」: DriverKitで美しく解こうとしない。CGEventTapで逃げる。できるだけ楽な道を選ぶ。
- 「選ぶことは捨てること」: 今回捨てるものは a) 有線USBマウス対応の厳密さ b) アプリ別プロファイルの初期実装 c) 水平スクロールの完全再実装。MVPでは捨てる。
- 「ユカイじゃない検出器」: 根本さんの違和感は「精密モードが切り替わったか分かりにくい」こと。UIで明確なインジケータ（メニューバー色変化、HUD）を出すべき。

## 確信度

- 技術方針 75%（高いが、進む戻るのエミュレーション区別は実機検証で覆る可能性 25%）
- 要件確信度 55%（製品型番・トリガーキー・UI形態が未確定。Yuna照合で上げる必要あり）

## 仮説

- 進む戻るはHID Consumer PageのAC Forward/Backではなく、ベンダーがKeyboard PageのCmd+[ を送っている。ならばIOHIDで区別可能。CGEventTapだけでは誤爆するので、IOHIDManagerでデバイスフィルタするハイブリッドが正解。
- 精密モードはdeltaスケールで十分。macOSのpointer accelerationは触らない。

## 次のアクション

- Yunaに「仕様の曖昧さと根本さんのBのズレ」を照合させ、Hayatoに「矛盾・過剰熱量」を刺させる。その後Hermesで技術検証、Gaiaで設計を固める。
