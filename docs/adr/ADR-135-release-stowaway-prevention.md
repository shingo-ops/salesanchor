# ADR-135: リリース相乗り防止 — develop を常に出荷可能に保つ

- **Status**: Accepted
- **Date**: 2026-06-12
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）
- **関連**: Ruleset 16619490（develop保護）/ Ruleset 15777895（main保護）/ ADR-121（SOP process-artifacts gate）/ docs/STANDARD-WORKFLOW.md / CLAUDE.md

## Context

develop→main のリリース PR に、develop へ蓄積された全変更が無差別に乗る構造のため、「Aだけ出すつもりがB/C/Dも本番に出る」相乗りが頻発した（#1910 / #1928 / #1931 / #1981）。直近の #1981 では、PO GO 前の migration（change_billing）が deploy.yml 修正のリリースに相乗りし、寸前の手動確認で発覚した。

根本原因：develop が「GO 待ちの待合室」と「リリースの出荷口」を兼ねており、両者は構造的に両立しない。

recon確定事実（5つの穴、2026-06-12 architect 確認）：
1. develop（Ruleset 16619490）に PR レビュー必須なし → 危険変更をセルフマージで develop に入れられる
2. main の必須ステータスチェックに process-artifacts gate が未登録 → リリース PR で gate が FAIL しても機械的にブロックされない
3. `.github/CODEOWNERS` が `migrations/`・`.github/workflows/deploy.yml`・`scripts/` をカバーしていない
4. main の Ruleset で require_code_owner_reviews が無効
5. feature→リリース PR のマージ間隔が 3 分など、人間が中身を確認できない速度で運用

## Decision

中心原則：**develop にマージされたものは「本番に出てよい」と見なす（develop＝常に出荷可能）。** そのために危険変更の関所を develop の入口に移す。

### A. CODEOWNERS 拡張（実施済み）

`.github/CODEOWNERS` に危険パスを追加してオーナーを明示する：
- `migrations/` → @shingo-ops
- `.github/workflows/` → @shingo-ops
- `scripts/` → @shingo-ops

### B. develop 入口関所（Code Owner レビュー必須）— PO GO 後に実施

develop 向け PR で危険パスを触る場合のみ Code Owner（Shingo）の承認を必須にする。
**通常の PR（フロント・通常ロジック）は従来どおり承認なしでCI緑のみでマージ可**。

実現手段：GitHub Ruleset（require_code_owner_review 有効化）。
**実機検証先行必須**：「危険パス PR が承認なしでブロック」「通常 PR は従来どおり通過」をテスト PR で確認してから適用。

### C. main 必須チェックへの process-artifacts gate 追加 — PO GO 後に実施

Ruleset 15777895 の required_status_checks に process-artifacts gate を登録。
リリース PR で gate が FAIL した場合、機械的にマージ不可とする。

### D. リリース PR テンプレートに相乗り確認欄を追加（実施済み）

PR テンプレートにリリース PR 用の確認欄を追加（変更ファイル一覧確認 + 危険パス報告手順）。

### E. 運用ルールのインライン明記（実施済み）

STANDARD-WORKFLOW.md と CLAUDE.md に以下をインラインで記載：
「migrations・deploy.yml・本番 scripts を含む実装は、PO GO が出るまで feature ブランチで待機し、develop にマージしない。develop へのマージ＝本番投入可の宣言と見なす。develop は待合室ではない。」

## Scope 外

- Terminal CC 用マシンアカウントの分離（別イニシアチブとして検討）
- main の bypass_actors（admin=shingo-ops）は維持（バイパスはログに残る）
- merge queue / リリースブランチ運用 / feature flag（今回は採らない・コスト過大）

## 実装上の注意

- B・C（Ruleset変更）はガバナンス設定の変更 → 不可逆操作扱い → **PO の明示 GO で適用**。
- B の設定可否は実機検証が先（GitHub Ruleset の組み合わせ動作を机上で確定しない）。
- 既存 CI チェック 11 件（develop）/ 10 件（main）は変更しない（追加のみ）。

## Consequences

### 受け入れ条件

- [ ] `migrations/` を触るテスト PR が Shingo の承認なしでは develop にマージできない（B 適用後）
- [ ] 通常フロントエンドのみの PR が承認なし・CI 緑のみで develop にマージできる（B 適用後）
- [ ] develop→main の リリース PR で process-artifacts gate が FAIL の場合マージできない（C 適用後）
- [x] PR テンプレートにリリース PR 用の相乗り確認欄が存在し変更ファイル一覧の報告が行われる（D）
- [x] STANDARD-WORKFLOW と CLAUDE.md に E のルールがインラインで存在する
- [ ] 上記をすべて満たした状態で通常リリース（develop→main）が 1 回問題なく完了する（B・C 適用後）
