# recon: guard-hex-increase 誤検知修正

## 調査対象

`scripts/check-design-token-ratchet.sh:25`

```bash
# 現行
matches=$(git show "${ref}:${file}" 2>/dev/null | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```

## 問題の事実

### 誤検知の発生経緯
PR #3285 (`release/tcg-line-import-stage1`) の CI で `guard-hex-increase` が FAIL。

```
frontend/src/pages/super-admin/TcgLineImportPage.tsx 0→4
```

### 原因
ADR-144 が必須とする `ui-allow` コメント書式:
```tsx
{/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
```
の `(#3285)` （PR 番号）が、ratchet 正規表現 `#[0-9a-fA-F]{3,8}\b` にマッチ。
`3285` は 16 進として有効な文字列（0-9 のみ）なため誤検知される。

実際の hex 色 direct 書きはゼロ件（全 inline style が `var(--...)` トークン）。

### grep オプション確認
`scripts/check-design-token-ratchet.sh:25` — `-E`（ERE）使用、`-P` ではない。
grep は lookbehind（PCRE）なし。

### index.css の (# hex ) パターン確認
`git show origin/main:frontend/src/index.css | grep -oE '\(#[0-9a-fA-F]{3,8}\)'`
```
(#2e7d32)   # line 112 CSS コメント: --success の色値参照
(#e53e3e)   # line 114 CSS コメント: --danger の色値参照
(#5b8dd9)   # line 258 CSS コメント: accent の色値参照
(#1e293b)   # line 330 CSS コメント: サーフェス色値参照
(#0f172a)   # line 331 CSS コメント: ページ背景色値参照
```
全 5 件が 16 進文字（a-f）を含む → PR 番号（十進のみ）とは区別可能。

## 関連 ADR
- ADR-067: デザイントークン強制（guard-hex ratchet の根拠）
- ADR-144: UI ガバナンス（`ui-allow: <理由> (#<番号>)` 書式の必須化）
