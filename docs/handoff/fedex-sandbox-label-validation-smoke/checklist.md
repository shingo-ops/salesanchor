# FedEx Sandbox ラベル発行 実機確認チェックリスト

**確認対象**: FedEx Label Validation — PDF / PNG / ZPL ラベル一括発行（PR #2300 実装）  
**実施者**: Shingo さん（画面操作）  
**前提**: Sandbox 認証情報（Client ID / Client Secret / Account Number）が登録済みであること  
**所要時間の目安**: 10〜15 分

---

## 事前確認（Sandbox 認証情報）

> Sandbox 認証情報が未登録の場合は **[Shingo 判断が必要な条件](#shingo-判断が必要な条件)** を参照してください。

- [ ] `https://app.salesanchor.jp/` にログイン済み
- [ ] 左メニュー → **「API 連携」** → **「FedEx」** を開く
- [ ] **「Sandbox」タブ** をクリック
- [ ] 以下の 3 項目が入力済みかどうか確認:
  - Client ID（空欄でないこと）
  - Client Secret（空欄でないこと）
  - Account Number（空欄でないこと）
- [ ] 未入力の場合は **[Shingo 判断が必要な条件](#shingo-判断が必要な条件)** へ

---

## 手順 1 — Label Validation タブを開く

1. 左メニュー → **「API 連携」** → **「FedEx」** を開く
2. **「Label Validation 申請支援」** タブをクリック
3. 「Step 1: アカウント番号登録確認」のチェックが緑（✅）になっているか確認
   - 赤（❌）の場合は Step 1 の Sandbox 認証情報の確認に戻る

---

## 手順 2 — サンプルラベルを発行する

1. 「**Step 2: テストラベルを発行**」セクションを確認
2. **「テストラベルを発行（4サービス）」** ボタンをクリック
3. 「発行中...」とボタンが変わることを確認（数秒〜30 秒かかる場合あり）
4. 発行完了後、以下の 4 サービスのラベル一覧が表示されることを確認:
   - IP（FedEx International Priority）
   - IE（FedEx International Economy）
   - IPE（FedEx International Priority Express）
   - FICP（FedEx International Connect Plus）
5. 各サービスに **3 つのボタン** が表示されることを確認:
   - **「PDF をダウンロード」**
   - **「PNG をダウンロード」**
   - **「ZPL をダウンロード」**

> エラーが出た場合はすぐにスクリーンショットを撮り **[確認結果の記録](#確認結果の記録)** の「エラー文」欄に記入してください。

---

## 手順 3 — PDF を確認する（IP サービスで代表確認）

1. IP（FedEx International Priority）の **「PDF をダウンロード」** をクリック
2. ダウンロードされたファイル（`fedex_lv_IP_*.pdf` 等）を開く
3. PDF が正常に開き、ラベル内容（送付先・追跡番号等）が表示されることを確認
4. 結果を **[確認結果の記録](#確認結果の記録)** に記入

---

## 手順 4 — PNG を確認する（IP サービスで代表確認）

1. IP（FedEx International Priority）の **「PNG をダウンロード」** をクリック
2. ダウンロードされたファイル（`fedex_lv_IP_*.png` 等）を開く
3. 画像として正常に開き、ラベルが表示されることを確認
4. 結果を **[確認結果の記録](#確認結果の記録)** に記入

---

## 手順 5 — ZPL を確認する（IP サービスで代表確認）

1. IP（FedEx International Priority）の **「ZPL をダウンロード」** をクリック
2. ファイルがダウンロードされることを確認（ファイル名: `fedex_lv_IP_*.zpl` 等）
3. ファイルをテキストエディタ（メモ帳・VSCode 等）で開く
4. ファイルの先頭が `^XA` で始まる ZPL コマンド文字列か、または Base64 文字列かを確認
5. 結果を **[確認結果の記録](#確認結果の記録)** に記入
6. ZPL stock type の確認（ブラウザの開発者ツール → ネットワーク → サンプルラベル発行リクエストのレスポンス JSON に `zpl_label_stock_type` フィールドがある）:
   - `STOCK_4X6` → フォールバックなし（正常）
   - `PAPER_85X11_TOP_HALF_LABEL` → フォールバックが使われた（記録要）
   - どちらでもない / フィールドがない → エラー扱い

> **開発者ツール不要の場合**: ZPL stock type の確認はスキップしても構いません。その場合は「unknown」と記入してください。

---

## 手順 6 — 全 4 サービスの追加確認（任意）

手順 3〜5 を IE / IPE / FICP にも繰り返す（時間が許す範囲で）。

> IP の 1 サービスのみ確認でも判断には十分です。

---

## 確認結果の記録

> 実施後にこの表を埋めてください。

**実施日時**: ____-__-__ __:__ JST  
**実施者**: Shingo

| 項目 | 結果 | メモ |
|---|---|---|
| PDF（IP） | PASS / FAIL | |
| PDF（IE） | PASS / FAIL / 未確認 | |
| PDF（IPE） | PASS / FAIL / 未確認 | |
| PDF（FICP） | PASS / FAIL / 未確認 | |
| PNG（IP） | PASS / FAIL | |
| ZPL（IP） | PASS / FAIL | |
| ZPL stock type | STOCK_4X6 / PAPER_85X11_TOP_HALF_LABEL（フォールバック） / unknown | |
| ZPL ファイル形式 | ZPL コマンド文字列（`^XA` 始まり） / Base64 / 不明 | |
| エラー文（あれば） | | |
| スクリーンショット有無 | あり / なし | 保存場所: |

---

## Shingo 判断が必要な条件

以下のいずれかに該当する場合は **作業を止めて** しんごさんの判断を仰いでください。Claude Code では対応できません。

| 条件 | 理由 |
|---|---|
| Sandbox の Client ID / Client Secret / Account Number が不明または未登録 | secrets 変更は Shingo のみ |
| FedEx Developer Portal でアカウント登録・認証情報取得が必要 | FedEx 外部 GUI 操作は Shingo のみ |
| FedEx 側でサービスタイプ（IPE / FICP 等）の有効化が必要 | 外部設定変更は Shingo のみ |
| ZPLII が STOCK_4X6 と PAPER_85X11_TOP_HALF_LABEL の両方で失敗 | FedEx Sandbox 設定または API 制約の可能性 — 要調査 |
| 本番アカウントでの確認が必要と判断した場合 | 本番 FedEx 操作は Shingo のみ |

---

## 参照

- `docs/handoff/fedex-sandbox-label-validation-smoke/recon.md` — 実装 file:line 引用
- `docs/adr/ADR-129-fedex-label-validation-wizard.md` — Label Validation Wizard 設計
- `docs/adr/ADR-123-carrier-integrator-provider.md` — FedEx Integrator 認定フロー
