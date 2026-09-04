# design: ci-hex-ratchet-fix

**対象ADR**: ADR-067（デザイントークン強制）, ADR-144（UIコンポーネントガバナンス）
**recon**: docs/handoff/ci-hex-ratchet-fix/recon.md

---

## KGI

guard-hex-increase が ui-allow コメントの PR 番号 `(#NNN)` を誤検知しなくなること。
正当な hex カラーコードの検出能力は維持されること。

## KPI（PO が画面・ログで一義に判定できる粒度）

| KPI | 検証方法 |
|-----|---------|
| PR#3285 の guard-hex-increase が PASS になる | `gh pr checks 3285` で green |
| 本 PR 自体の guard-hex-increase が PASS になる | `gh pr checks <本PR番号>` で green |
| `#fff` `#1a2b3c` `#ABCDEF80` は検出される | recon 手順3の検算で3件確認済み |
| `(#3285)` `(#3165)` `(#abc)` は検出されない | recon 手順3の検算で0件確認済み |

---

## 変更内容

### `scripts/check-design-token-ratchet.sh`（1行変更）

**変更前**（行25）:
```bash
matches=$(git show "${ref}:${file}" 2>/dev/null | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```

**変更後**:
```bash
# (# ... ) 形式（PRリンク・ui-allow番号等）を除去してから計測する。
# -E grep は後読みが使えないため sed で前処理する（macOS/Linux 両対応）。
matches=$(git show "${ref}:${file}" 2>/dev/null | sed -E 's/\(#[0-9a-fA-F]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```

---

## 修正方針の選択根拠

**採用: `sed -E` 前処理方式**

| 方式 | 採否 | 理由 |
|------|------|------|
| grep `-P`（PCRE）+ 否定後読み `(?<!\(#)` | 不採用 | GNU grep 固有。macOS BSD grep は `-P` 非対応 |
| sed で `(#...)` を先に除去 + 既存 grep | **採用** | macOS/Linux 両対応（GNU sed / BSD sed 両方 `-E` 対応）|

**sed パターン**: `s/\(#[0-9a-fA-F]+\)//g`
- `\(` / `\)`: 丸括弧のリテラル（ERE でのエスケープ）
- `#[0-9a-fA-F]+`: `#` に続く1文字以上の hex 文字
- `g`: 行内全置換

---

## 弊害・リスク

| リスク | 評価 | 対策 |
|-------|------|------|
| CSS コメント内の `(#2e7d32)` 等も除去され計測値が変わる | 低（BASE・HEAD 両方で同数減少。ラチェット判定に影響なし） | recon 手順3で確認済み |
| `(#color)` 形式のインラインCSS値を見逃す | 低（CSS プロパティ値は通常 `color: #fff` 形式。丸括弧包みは稀） | 発生したら ALLOWED_EXCEPTIONS で個別対応 |
| 将来の PR 番号が hex 文字のみ（例: `#cafe`）の場合は正しく除去される | 影響なし（PR番号は除去して正しい） | — |

---

## 戻し方

```bash
git revert <merge-commit>  # 1行の変更のみ。migration なし
```

---

## 外部事例

GitHub Actions の ratchet/lint スクリプトで `grep -oE '#hex'` が JSDoc の `{#color}` や URL フラグメント `(#anchor)` を誤検出するケースは一般的（ESLint ratchet / Stylelint rule count ratchet で同様の問題報告あり）。
対策として "strip comments before counting" または "use AST-based counting" が推奨パターン。
本実装は前者の軽量版（コメント全除去でなく `(#...)` パターンのみ）。
