# Modal footer limited review

基準HEAD 7606ca9a041e315b81040373e8f4ddebbc562133。read-only、別AI起動なし。

## 暫定判定

APPROVE（コード差分と検証計画に限定）。実3部品ブラウザー/品質検査は実行中なので検収全体の合格ではない。

設計§AI/card01は実運用3footer、金額span、短高360/通常900、7幅（640は実zoomではない）、日英/明暗、保存中/既存なしを対象とし、座標のdialog/viewport内、文字欠け、行非重複、一行条件の前後同値、Tab/ShiftTab、外部formを検査する。前回の合成Shippingだけの検査不足を補う計画として重大不足なし。金額0/通常/大額の具体入力値は実行証跡へ記録する。未指定の任意長文字は保証対象外。

## 実装差分

- Modal.css:84にflex-wrap:wrapのみ追加。他宣言不変。
- Modal.stories.tsx:2にuseTranslation import、:88以降ResponsiveFooterを追加。共通Button3個、既存shipping/common翻訳、開閉のみ。既存4story差分なし。グローバルテーマ操作・API通信追加なし。
- git diff --stat -- frontend は指定2ファイル22行追加のみ。AHの6製品差分は現treeから解消。退避7ファイルのhash保証は別担当の実績を確認後に採用する。

私はCSS/TSX差分と設計を読取確認した。ブラウザー/品質試験は再実行していない。最終hashと実測はGenerator完了後に別途判定する。

確認時hash（最終manifestではない）:
frontend/src/components/Modal.css 0715a72e3898b3f78993415159dd4d6d9076527a04787786986751312f599a52
frontend/src/components/Modal.stories.tsx 15589cf2d1b39367c5c76858518e9e47fc5654ee54d5a51a3de8465eb87498da

## fixture原物同一性の補足

before/after各5ファイルを比較。beforeは固定7606ca9a、afterは現worktreeへ照合。3部品とModal.tsxの差分はimport参照先のみで、JSX/状態/イベント/文字列は完全一致。before/after Modal.cssは各原物と完全一致し、両者の差分はfooterのflex-wrap:wrapだけ。fixtureが共有参照するButton.tsx/Button.css/icons.tsx/InventoryPicker.tsxも固定baseと現物が完全一致。

import変換: API→mock-api、Shipping auth→mock-firebase、PurchaseOrdersのInventoryPicker→実worktree絶対パス、Modal→fixture相対パス、Modal内部Button/Icon→実worktree絶対パス。

製品2hashは前回暫定レビューと一致:
- Modal.css: 0715a72e3898b3f78993415159dd4d6d9076527a04787786986751312f599a52
- Modal.stories.tsx: 15589cf2d1b39367c5c76858518e9e47fc5654ee54d5a51a3de8465eb87498da

今回の判定は複製同一性だけ。ブラウザー結果・APIモックの全通信遮断・操作の十分性は未判定。

## 最終限定検収

APPROVE。検査の再実行ではなく、原稿・保存結果・製品実物の照合によるレビュー。

- v4限定5組PASS。全560組PASS。実3部品/7幅/2高さ/日英/明暗/10データ状態を照合。referenceMatched/beforeUnchanged全560true、自然幅一行対象448組、after内容領域/viewport/文字欠け違反0。改修前の単行縮小を自然幅で区別する。金額は0/123450/999999999999。
- future発送共通Button390px日英2組PASS。実3部品の外部formとTab/ShiftTab、submit1回は別3組を記録。
- modal-focus補助は448ボタンの輪郭がdialog/viewport内かつ隣接子と非重複、Tab/ShiftTabを検査してPASS。Enter/Spaceで外部form送信6組もPASS。外部通信0、console/page error0。
- Story4条件PASS。保存された子文言も日英切替実在を確認。明暗2×日英2、3ボタン内側配置、閉じる操作を確認。
- root-quality/results.jsonはeslint/coverage/check-all/build/storybook全exit0。coverage.logは22files189tests成功。diffcheck0はmanifest記録。
- modal-manifest2SHA256と現物は2/2一致し、前回暫定レビューから製品変更なし。CSS追加wrap1宣言、Story追加のみへのコードAPPROVEを適用。

残る限界: Chromium/モック条件の検査。実ブラウザーzoomではなく640px相当幅。任意長文字・任意金額・全本番画面/PO目視は保証しない。ここでのAPPROVEは本便限定の実装検収でありPR番号付きGO・マージ・本番反映承認ではない。
