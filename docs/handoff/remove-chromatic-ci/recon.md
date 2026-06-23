# recon: Chromatic CI 削除

## 目的

`.github/workflows/chromatic.yml` を削除して、今後の PR で `Chromatic Snapshot` / `UI Tests` の status が出ないようにする。残す視覚ゲートは Karte / ADR-067 dark mode / Storybook build。

## file:line 根拠

| 引用先 `path:line` | 確認内容 |
|---|---|
| `docs/handoff/remove-chromatic-ci/evidence.md:1-39` | 削除対象 Chromatic workflow の写し。job は `Chromatic Snapshot` 1つだけで、`chromaui/action@latest` により Chromatic 側の status を生成していた |
| `docs/handoff/remove-chromatic-ci/evidence.md:13-39` | `needs:` 依存なし。workflow を消しても他 job への連鎖依存は無い |
| `.github/workflows/frontend-check.yml:71-89` | `Storybook build check` は Chromatic と別 job で独立している |
| `.github/workflows/e2e.yml:55-89` | `Lint & Dark Mode Check (ADR-067)` は別 workflow / 別 status で残る |
| `.github/workflows/karte-gate.yml:34-145` | `Karte Visual Gate (chromium)` は別 workflow / 別 status で残る |
| `docs/BRANCH_PROTECTION_SETUP.md:287-294` | Legacy / ruleset の required checks に Chromatic / UI Tests は含まれていない |
| `docs/adr/ADR-073-design-system-kgi-rubric.md:74-78` | Chromatic 等の visual regression は現フェーズでは対象外で、手動確認で代替する方針が明記されている |

## 結論

- workflow 削除だけで今後の Chromatic status 発行は止まる
- branch protection / ruleset の更新は不要
- 残りの visual gates は Storybook / ADR-067 dark mode / Karte
- #2507 の既存 pending `UI Tests` は、削除後に当該ブランチを rebase / 再 push して初めて解消される
