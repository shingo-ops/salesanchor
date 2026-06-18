# FedEx Sandbox Label Validation 実機確認チェックリスト（PDF / A4）

**確認対象**: FedEx Label Validation — PDF ラベル一括発行（A4通常プリンター / PDF のみ）  
**実施者**: Shingo さん（画面操作）  
**前提**: Sandbox 認証情報（Client ID / Client Secret / Account Number）が登録済みであること  
**所要時間の目安**: 5〜10 分

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
5. 各サービスに **「PDF をダウンロード」ボタンのみ** が表示されることを確認

> エラーが出た場合はすぐにスクリーンショットを撮り **[確認結果の記録](#確認結果の記録)** の「エラー文」欄に記入してください。

---

## 手順 3 — PDF を確認する（4 サービス）

各サービスで **「PDF をダウンロード」** をクリックしてください。

1. IP（FedEx International Priority）の PDF をダウンロードして開く
2. IE（FedEx International Economy）の PDF をダウンロードして開く
3. IPE（FedEx International Priority Express）の PDF をダウンロードして開く
4. FICP（FedEx International Connect Plus）の PDF をダウンロードして開く

各 PDF について確認すること:
- ファイル名: `fedex_lv_{サービス略称}_{追跡番号}.pdf`
- PDF が正常に開き、ラベル内容（送付先・追跡番号等）が表示される

> 時間がなければ IP の 1 サービスのみ確認でも判断には十分です。

---

## 手順 4 — 印刷確認（任意）

PDF をプリンターで印刷し、A4 用紙にラベルが正常に印刷されることを確認する。

> Label Validation 申請にはラベル印刷が必要です。

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
| 本番アカウントでの確認が必要と判断した場合 | 本番 FedEx 操作は Shingo のみ |

---

## 参照

- `docs/handoff/fedex-sandbox-label-validation-smoke/recon.md` — 実装 file:line 引用
- `docs/adr/ADR-129-fedex-label-validation-wizard.md` — Label Validation Wizard 設計
- `docs/adr/ADR-123-carrier-integrator-provider.md` — FedEx Integrator 認定フロー
