# recon: AI が足した見張りを記録できる道（草案・2026-11-09）

状態: 草案（PO 未承認）。発端は 2026-11-09 の週次点検（同意と権限）で、見張りの変更3件が `ABNORMAL_REASON=B` に出たこと。PO の言葉（2026-11-09）:「原則私はエンジニアではないから見張りを足すのはあなたと実行者だけ」。

## 既存 ADR の検索
- `git grep -il 'hook' origin/main -- docs/adr/` と FEATURE-INDEX から、関係するものは次の3つ。
  - ADR-1034（Opus の権限の足し引きと台帳）: 見張りの登録と本体は「Opus が自分では変えないもの」で、変化には PO 記録が要る（docs/handoff/permission-delegation/design.md:65-67）。
  - ADR-1033（会話の同意票）: PO 記録の形 `consent:<鍵>`。
  - ADR-1029（マージ前の Opus 審査をフックで強制）: PR は新しく起動した審査役（opus）の APPROVE が無いとマージできない。

## 観測した事実
1. 今週の B 3件の中身（scratchpad の map_hooks.py。consent-audit.py と同じ式）:
   - hook_files `29ac3748|9e086e1e` = ~/.claude/scripts/mac-test-guard/guard.py。中身の sha256 の先頭8桁 `9e086e1e` は origin/main の `scripts/agent-hooks/mac-test-guard/guard.py` と同じ（`git show origin/main:… | shasum -a 256`）。
   - user:hooks `+PreToolUse|Bash|3ba846f5` = mac-vm-guard.py と mac-test-guard/guard.py の組。`-PreToolUse|Bash|062521a7` = mac-vm-guard.py だけの旧版。
   - 入れたのは PO の `!` による `scripts/agent-hooks/mac-test-guard/install.sh`（docs/handoff/mac-test-guard/design.md:77）。設計・実装は PR #5039・#5049（GitHub main にマージ済み）。
2. 見張りの PR 番号での説明は、repo の settings.json（repo-allow・repo-hooks）だけに限られる: /Users/tanizawashingo/.salesanchor-tools/scripts/dev/consent-audit.py:801（PR_ONLY_TARGETS）・`:906`（それ以外の B は PR 番号では通らない）。理由は「Opus は自分で PR をマージできるので、PR は PO の確認の証にならない」（docs/handoff/permission-delegation/design.md:328）。
3. user:hooks・hook_files を説明できるのは、本文にハッシュを含む同意票（PO の「1」）だけ（同 design.md:197）。台帳の分類は perm-change.py:669 で `reserved:R4`。
4. 見張りを ~/.claude に入れる作業は、Claude Code の自動判定が「AI が自分の設定を変える」として止めるため、今は PO の `!` で台本を走らせている（同 design.md:225、mac-test-guard/design.md:82）。
5. 11/02 の週次点検でも同じ形の B（見張りを足した変更）が出て、Opus は記録できなかった（~/CC報告ファイル-keep/consent-weekly/20261102-changes-analysis.md）。

## 未確認
- 自動判定に1行足す例外（下の HKI-1）が、AI による install.sh の実行を実際に通すか。PDL-1 は同じ形で通っている（ADR-1034 便1）が、見張りの登録を直接変える台本で通るかは試していない。
