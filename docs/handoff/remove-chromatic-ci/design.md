# design: Chromatic CI 削除

## recon

`docs/handoff/remove-chromatic-ci/recon.md`

## 対象ADR

ADR-073 (`docs/adr/ADR-073-design-system-kgi-rubric.md`)

## 外部・過去事例の参照と我々への応用

- ADR-073 は Chromatic 等の visual regression を現フェーズの対象外としており、ここでは CI 上の Chromatic 配線を外しても設計と矛盾しない。
- 既存の visual gate は Karte / ADR-067 dark mode / Storybook build に分散しているため、Chromatic だけを削除しても他の視覚確認は維持される。

## 変更内容

`.github/workflows/chromatic.yml` を削除する。これにより今後の PR では `Chromatic Snapshot` / `UI Tests` status が出力されない。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `.github/workflows/chromatic.yml` が削除されている | `test -f .github/workflows/chromatic.yml` が失敗する |
| 今後の PR で Chromatic status が出ない | workflow 差分がない新規 PR で `Chromatic Snapshot` / `UI Tests` が表示されないことを確認 |
| 残りの visual gates が維持される | `Storybook build check` / `Lint & Dark Mode Check (ADR-067)` / `Karte Visual Gate (chromium)` が従来通り実行される |
| branch protection / ruleset 更新が不要 | `docs/BRANCH_PROTECTION_SETUP.md` と ruleset の required checks を確認 |
| #2507 の pending `UI Tests` が解消する | Chromatic 削除後に #2507 を rebase / 再 push して status が消えることを確認 |

## 弊害・トレードオフ

- Chromatic による自動 visual regression の網は外れるが、残る 3 つの visual gate でページ構造・dark mode・Karte 表示を継続確認できる
- 既存 PR の pending status は自動では消えないため、#2507 は rebase / 再 push が必要

