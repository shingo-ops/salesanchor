<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — デザイントークン週次監査の Discord 送信失敗の直し

**対象ADR**: ADR-035（L5 Owner ping）／ ADR-067（デザイントークン強制）  
**recon**: docs/handoff/design-token-audit-notify-path/recon.md  
**日付**: 2026-11-24  
**担当**: Planner（Opus 設計担当）  
**状態**: 設計案作成済み・自己審査済み（APPROVE）・PO 実装承認済み（2026-11-24「1」）・クラウドの Sonnet が実装し push 済み（ef240f03b）・Opus が手元で照合済み（新規2ファイルはカードと一致・試験 8 本 OK・点検 143 件 不一致 0 件）・合流と本番での確認は未了

---

## KGI（PO が○×で判定できる形）

1. 未使用のデザイントークンが見つかった週、Discord の「定期の報告」に「🎨 未使用デザイントークン N 件検出」が 1 件届く。「急ぎ」には 0 件。
2. 同じ種類の間違い（作業場所の指定がずれて、呼ぶ台本が見つからない）は、次に誰かが書いても PR の自動確認で赤になり、main に入らない。

PO 承認: 2026-11-24 PO「1」（「直す設計を作る」を選択）。設計そのものの承認と実装の承認はまだ。

---

## 外部・過去事例の参照と我々への応用

- 該当なし：原因はこのリポジトリの設定 1 行の作業場所ずれで、実行記録（exit 127・No such file）で確定している。外部事例で裏付ける判断が無い。
- 過去事例（社内）: 同じ送信台本を使う weekly-deploy-lock-count.yml・weekly-stale-tasks.yml は根元から呼び、2026-11-23 に HTTP 204 で届いた（recon 実測）。→ 応用: 送信台本は根元からの道で呼ぶ形にそろえる。

---

## 対象と対象外

- 対象: `.github/workflows/design-token-audit.yml:82` の 1 行／新しい点検台本と試験／`.github/workflows/test.yml` に点検の段を 2 つ足す。
- 対象外（触らない）: 監査の中身（frontend/scripts/check-unused-tokens.js）・未使用トークン 40 件の片付け・Issue 作成の段・送り先の secret・他の workflow・`.github/workflows/workflow-lint.yml`。

---

## 変更前後

### 1. 送る段の道を直す（`.github/workflows/design-token-audit.yml:82`）

変更前:
```
          bash scripts/notify/discord-owner-ping.sh "$MSG"
```
変更後:
```
          bash ../scripts/notify/discord-owner-ping.sh "$MSG"
```
選んだ理由: job 既定の作業場所 frontend は監査の段（26行 `node scripts/check-unused-tokens.js`）が使うので変えない。送る段だけ 1 つ上を指す。下の点検は frontend/../scripts/... を正しく解いて実在を確かめられる。
代わりの案: 段に `working-directory: ${{ github.workspace }}` を足す → 点検が `${{` を解けず確かめの外になるため採らない。

### 2. 同じ間違いを止める点検（新規）

- 新規 scripts/ci/check_workflow_script_paths.py（標準ライブラリ＋PyYAML。同じ job で動く `scripts/ci/check_queue_triggers.py:21` が既に `import yaml` しているので追加の入れ物は要らない）
  - .github/workflows 配下の yml・yaml を全部読む。
  - 各段の `run:` から `bash|sh|node|python|python3 [-I] <道>` で `<道>` が `scripts/` を含む相対の道を拾う。`$` を含む道は飛ばす。
  - 作業場所 = 段の `working-directory` → job の `defaults.run.working-directory` → workflow の `defaults.run.working-directory` → `.` の順。`${{` を含めば飛ばす。
  - run 内で拾った位置より前の、行全体が `cd <道>` の最後の行があれば作業場所に足す（`$` を含めば飛ばす）。
  - 正規化した道が `git ls-tree -r --name-only HEAD` に無ければ「ファイル名・job・段の名前・作業場所・道」を出して終わりの値 1。全部あれば件数を出して 0。
  - `git ls-tree` を使う理由: test.yml の点検 job は sparse-checkout（`.github/workflows/test.yml:277`）で frontend を持ってこないため、作業ツリーの実在確認では誤る。
- 新規 scripts/tests/test_check_workflow_script_paths.py（`scripts/tests/test_check_queue_triggers.py` と同じ書き方）: 最低 4 件。①job 既定 frontend＋根元の道 → NG ②同じで `../` → OK ③`cd backend` の後の ../scripts/... → OK ④`$` を含む道 → 飛ばす。
- `.github/workflows/test.yml:288` の後に 2 段を足す:
```
      - name: Test the workflow script path checker
        run: python3 -I scripts/tests/test_check_workflow_script_paths.py -v
      - name: Check script paths called from workflows
        run: python3 -I scripts/ci/check_workflow_script_paths.py
```

試しの点検（recon 実測）: 現状 141 件中 NG 1 件（変更1の行）。変更1の後は 0 件の見込み。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 点検が直す前の main で 1 件を NG にする | 実装 PR で変更1を戻した状態の python3 -I scripts/ci/check_workflow_script_paths.py の終わりの値が 1・出力に design-token-audit.yml（実装役の生出力） |
| K2 点検が直した後で 0 件 | PR の CI「Check script paths called from workflows」緑 |
| K3 点検の試験 4 件以上が通る | PR の CI「Test the workflow script path checker」緑 |
| K4 Discord「定期の報告」に 🎨 の知らせが 1 件・「急ぎ」0 件 | main 反映後に design-token-audit.yml を手動実行 → 実行記録に `Discord response HTTP status: 204`、2 チャンネルを Bot で読む（K4 確認と同じ読み方） |
| K5 次の月曜 2026-11-30 の定時実行が success | `gh api repos/shingo-ops/salesanchor/actions/workflows/design-token-audit.yml/runs?per_page=1` の conclusion |

---

## 技術 How・KPI

- KPI: 週次監査の結論 failure の連続 3 回 → 0 回。全 workflow の台本の道の不一致 1 件 → 0 件（以後 0 を CI で守る）。
- 技術選択: 既存の CI 点検の並び（test.yml の点検 job）に足す。新しい workflow は作らない（必須チェックの付け替えが要らない）。

---

## 弊害・トレードオフ

- 直した後は未使用トークン 40 件が片付くまで、毎週月曜に「定期の報告」へ 1 件届く → この仕組みの元の狙いどおり。うるさければ片付けか止めるかを別テーマで PO に聞く。
- 点検の誤検知（`cd` の入れ子・関数内など）→ 拾うのは行全体の `cd` だけで、迷う形は `$` で飛ばす。誤検知が出たら試験を足して直す。止まった PR は点検の出力で場所が分かる。
- test.yml の変更 → 必須チェック job の中に段を足すだけで、job 名・needs は変えない（`scripts/ci/check_ci_aggregators.py` の対象を壊さない）。

戻し方: 実装 PR を revert（変更1は 1 行、点検は新規ファイルと test.yml の 2 段）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | この設計の PO 確認と実装承認 | PO |
| 2 | 実装カードどおりに変更1・点検・試験・test.yml を 1 PR で（K1 の生出力を PR に添える） | クラウドの Sonnet |
| 3 | CI 緑・審査役（reviewer・opus）APPROVE・確認済みコメントの後に合流 | Opus（GO 委任） |
| 4 | 手動実行で K4、11/30 の定時で K5 を確かめて PO へ報告 | Opus |

実装カード: 上の「変更前後」が全文。触ってよいのは 4 ファイル（design-token-audit.yml・test.yml・新規 2 本）だけ。危険な道（migrations/・deploy.yml・本番 scripts/）は含まない。

---

## 継続

- 守り手: scripts/ci/check_workflow_script_paths.py（test.yml の必須 job で毎 PR に走る）。
- 完了後の監視: 2026-11-30 の定時実行の結論（K5）。
- 次フェーズへの引き継ぎ: 未使用トークン 40 件の扱い（片付けるか知らせを止めるか）は別テーマ。

---

## 設計審査（Architect・同一 AI の自己審査）

- 判定: APPROVE
- 根拠: 原因は実行記録で確定（exit 127）。変更は 1 行で、作業場所を変えないので監査の段に影響しない。点検は現状 141 件に試しに当てて NG 1 件（狙いの行だけ）・cd を考えた後の誤検知 0 件。受け入れ基準は全部コマンドか CI の名前で○×が出る。
- 未解決: 無し。
