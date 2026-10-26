branch: release/ci-pin-e2e-runner

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/ci-pin-e2e-runner | CI の画面検査が ubuntu-26.04 で「1件も走らない」赤になるのを ubuntu-24.04 固定で直す（e2e.yml の Playwright 2ジョブ） | 2026-10-26 14:58 | IN_PROGRESS | | | karte-gate.yml:38 が2026-10-24 に同じ理由で既に固定済み＝同じ直し方の横展開。PR #4780（Popover 金型）の画面検査がこれで塞がれているため先行して出す |
