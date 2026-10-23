# recon: karte-gate-run の実行環境固定

実測時の origin/main SHA: 50d7f52da9bf44e92ce87eaa62bf41667301dca5

## 事実（生出力は /tmp/CC報告ファイル/discord-pdca-bin15/karte-cause/ と /tmp/CC報告ファイル/karte-runner-pin/）

1. 変更前の実行環境指定
   - /Users/tanizawashingo/worktrees/salesanchor/release-karte-gate-runner-pin/.github/workflows/karte-gate.yml:37 `runs-on: ubuntu-latest`（ジョブ karte-gate-run）
   - 同ファイル :22（detect-changes）と :133（karte-gate）にも ubuntu-latest がある。本便では触らない。

2. 成功 run 39900317374 の実行環境
   - /tmp/CC報告ファイル/discord-pdca-bin15/karte-cause/log-success-39900317374.txt:183 `Image: ubuntu-24.04`
   - 同 :184 `Version: 20261012.334.1`

3. 失敗 run 39929732953 の実行環境
   - /tmp/CC報告ファイル/discord-pdca-bin15/karte-cause/log-fail-39929732953.txt:17 `Image: ubuntu-26.04`
   - 同 :18 `Version: 20261012.163.1`
   - 同 :210 `Cannot install dependencies for ubuntu26.04-x64 with Playwright 1.59.1!`

4. 失敗画像では日本語が豆腐になり、レイアウトは同一（前段の原因調査 /tmp/CC報告ファイル/discord-pdca-bin15/karte-cause/ による）。

5. 基準画像の履歴
   - frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/karte-customer-company-chromium-linux.png
   - frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/karte-lead-deal-chromium-linux.png
   - `git log -1 -- frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/` の結果: b93850a3f 2026-06-13（以降の変更なし）

6. 既存 ADR 検索
   - `git grep -il "karte" docs/adr/` の結果: ADR-064, ADR-108, ADR-110, ADR-127, ADR-134, ADR-136, README.md
   - `grep -in karte docs/adr/FEATURE-INDEX.md` の結果: 該当なし
   - 画面検査の実行環境固定を決めた ADR はなし。関連: docs/adr/ADR-110-karte-reference-alignment.md（カルテ見本一致）
