# recon: ci-hex-ratchet-fix

作成日: 2026-09-05
ブランチ: `release/fix-hex-ratchet-pr-number`

---

## タスク概要

`scripts/check-design-token-ratchet.sh` の hex 検出正規表現が、
`ui-allow` コメントの PR 番号表記 `(#3285)` を色コードと誤認し guard-hex-increase を誤 FAIL させる問題を修正する。

---

## 既存 ADR 検索結果

- `docs/adr/ADR-067-design-token-enforcement.md` — デザイントークン強制ルール（hex 禁止・tokens.css SSoT）
- `docs/adr/ADR-144-ui-component-governance.md` — ui-allow コメント書式を `(#PR番号)` と定義

---

## 衝突の事実

UI governance gate（ADR-144）は `ui-allow` コメントに `(#PR番号)` 形式を要求する:
```tsx
{/* ui-allow: reason (#3285) */}
```

一方、guard-hex-increase ラチェットは以下の正規表現で hex を計測する:
```bash
grep -oE '#[0-9a-fA-F]{3,8}\b'
```

`3285` は `[0-9a-fA-F]` の部分集合（全て 0-9 の数字）であるため、
`#3285` が 4桁 hex カラーコードとして誤検出される。

---

## 過去の発生例

| PR | 内容 | 影響 |
|----|------|------|
| #3285 | MIG-04 Stage 1 LINE import (`TcgLineImportPage.tsx`) | ui-allow 4件 → `0->4` で FAIL |
| #3165 | 旧 MIG-04 UI PR（閉鎖済） | 同様の ui-allow コメント含む |

---

## 対象ファイル

### 変更
- `scripts/check-design-token-ratchet.sh:25` — `count_hex_in_ref_file` 関数の matches 計測行

---

## 手順3 検算結果（生出力）

```
=== 修正前: hex_positive.txt（期待: 3件）===
#fff
#1a2b3c
#ABCDEF80
=== 修正前: hex_negative.txt（修正前は誤検出あり）===
#3285
#3165
#abc
```

```
=== 修正後ロジック: hex_positive.txt（期待: 3件）===
#fff
#1a2b3c
#ABCDEF80
=== 修正後ロジック: hex_negative.txt（期待: 0件）===
（出力なし）
```

| ファイル | 修正前 BASE→HEAD | 修正後 BASE→HEAD | ラチェット判定 |
|---------|-----------------|-----------------|--------------|
| `frontend/src/index.css` | 187→187 | 182→182 | PASS（変化なし）|
| `frontend/src/tokens.css` | 除外 | 除外 | 対象外 |
| `TcgLineImportPage.tsx` | 0→4 (FAIL) | 0→0 (PASS) | 修正 ✓ |

index.css の 187→182 は CSS コメント内に `(#2e7d32)` 等の色参照が5件あり、
sed で同時除去される副作用。BASE・HEAD 両方で同数減少するためラチェット判定は変わらない。
