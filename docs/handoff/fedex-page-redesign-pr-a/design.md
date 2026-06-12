# Phase 3 設計 — fedex-page-redesign-pr-a

**対象ADR**: ADR-129  
**recon**: docs/handoff/fedex-page-redesign-pr-a/recon.md  
**日付**: 2026-06-12  
**担当**: Planner（Shingo承認済み）

---

## 外部・過去事例の参照と我々への応用

- 事例1: Stripe Dashboard の OAuth設定画面 — 認証情報は「表示モード（マスク済みキー確認）」と「編集モード（新規入力）」を分離。常時フォームを開いておくデザインは "入力しないといけないのか" という誤解を生む。我々への応用: 状態カードをデフォルトとし、フォームは明示アクション時のみ展開。
- 事例2: AWS Console の IAM アクセスキー画面 — 秘密鍵はフル表示しない（生成時のみ1回表示）。我々への応用: `client_id_hint` をそのまま表示し、フル値はフロントへ送らない。
- 事例3: Twilio Console の Credentials 画面 — 本番/テスト環境を独立カードで並置し、それぞれ接続状態バッジを表示。我々への応用: FedEx の本番/Sandbox を2カードで並置し、バッジで状態を一目確認できる設計。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| FedEx設定タブに本番・Sandboxの2カードが表示される | Shingo実機確認（Playwrightスクリーンショット） |
| 状態カードがデフォルト、フォームは[編集]押下時のみ展開 | Shingo実機確認（操作フロー確認） |
| APIキーはマスク済みhintのみ表示（フル値なし） | コードレビュー: `CarrierIntegrationPage.tsx` `client_id_hint` 参照のみ |
| 保存成功後に自動接続テストが走りバッジが更新される | Shingo実機確認（test-connection自動呼び出し確認） |
| 削除ボタン押下でConfirmModal（影響説明付き）が表示される | Shingo実機確認 |
| タブ名が「連携ガイド」に変わっている | Shingo実機確認 |
| DHL / UPS の動作が変わっていない | CI lint + 変更ファイル確認（CarrierIntegrationPage.tsx のみ） |
| i18n キーが ja/en 両方に追加されている | CI lint（local/no-japanese-literal） |
| デザイントークン規約準拠（ADR-067） | CI: check:new-tokens / check-css-hardcoded-values PASS |

---

## 技術 How・KPI

- **KPI**: 設定ページの「どこを触ればよいか不明」フィードバックがゼロになること（Shingo実機確認）
- **技術選択**: 既存の `Card` / `Badge` / `ConfirmModal` コンポーネントを活用（新規コンポーネント作成なし）
- **状態管理**: `editingEnv: Env | null` で編集中の環境を一元管理。FedExは `prodData` + `sandboxData` の2状態を並行保持

---

## 弊害・トレードオフ

- コンポーネントの行数が増加（旧: 347行 → 新: 約460行）→ 仕様上必然の複雑度増。`renderCard` 関数で3状態(view/edit/empty)を分離し可読性を維持
- `busy` フラグが全環境共通（どちらのカードのボタンも同時にdisabledになる）→ 同時操作を防ぐシンプルな設計として意図的

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | CarrierIntegrationPage.tsx 全面改修（view/edit分離） | Generator |
| 2 | i18n ja/en 新規キー追加（24キー） | Generator |
| 3 | pages-layout.css CSS追加 + tokens.css トークン追加 | Generator |
| 4 | lint / tsc / stylelint / 全フック通過確認 | Generator |
| 5 | PR作成 → CI通過 → Shingo実機確認 | Shingo |
| 6 | develop マージ → 本番デプロイ（PR-B1へ） | Shingo |

---

## 継続

- 完了後: PR-B1（連携ガイド骨格実装）へ移行
- Part B 実装時は FedexLabelValidationTab.tsx を全面作り替え予定
- スクリーンショット撮影（Shingo）は PR-B2 で実施
