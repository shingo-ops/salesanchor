# recon: GO 委任の範囲に「設計どおりの計画」を追加する

基準: origin/main 4667364b1（2026-10-15）

## 既存 ADR の検索
- docs/adr/ADR-1003-go-delegation-to-opus.md：GO 発行を Opus へ常時委譲する（例外あり）。解除は PO の「委譲停止」。
- docs/handoff/go-record-transcription/opus-delegation.md：委任の正式記録。範囲は「必須 CI 通過・Reviewer APPROVE・PO への3行報告」を満たす PR の GO。

## 現在地（file:line）
- /Users/tanizawashingo/worktrees/salesanchor/release-go-delegation-design-scope/CLAUDE.md:30 無制限鍵での変更を伴う作業（DB 書き込み等）は「作業ごとに PO の GO が必要」。
- /Users/tanizawashingo/worktrees/salesanchor/release-go-delegation-design-scope/CLAUDE.md:57 GO 権限は PO。ADR-1003 により例外を除き Claude Opus へ常時委譲。
- /Users/tanizawashingo/worktrees/salesanchor/release-go-delegation-design-scope/docs/handoff/go-record-transcription/opus-delegation.md の「範囲」節は PR の GO だけを書いており、無制限鍵での本番変更には触れていない。

## PO 発言（2026-10-15、閲覧専用ページの設計の壁打ち中）
- 「N,仕様に関しては壁打ちして決めているので仕様から逸脱していないGOは全てOPUSに権限委譲する」
- 「N,設計をした計画に関してはGOを出す権限を恒久的にあなたに与えたい、ただし設計から逸脱した場合は私に報連相をして壁打ちし直すことを条件とする、OPUSは管理者なので恒久的に許可を権限委譲したいと考えている」
