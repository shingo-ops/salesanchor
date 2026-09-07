# 便1 破棄後のKGI②分母再測定

> この文書は何か: 便1破棄後、KGI②の分母を正しく測り直した記録（index.css=色トークン正本を分母から除外）。

親リンク: [../../specs/design-system/migration.md](../../specs/design-system/migration.md)

## 前提

- PR #2808 は破棄済み
- 色トークン正本は `frontend/src/index.css`
- `frontend/src/tokens.css` は分母から除外

## 手順4a: 真のページ側ベタ書き

実行コマンド:

```bash
grep -rEn "#[0-9a-fA-F]{3,8}\b" frontend/src --include="*.css" --include="*.tsx" --include="*.jsx" --include="*.ts" | grep -vE "frontend/src/(index|tokens)\.css" | tee /tmp/true-hex.txt | wc -l
cut -d: -f1 /tmp/true-hex.txt | sort | uniq -c | sort -rn | head -20
```

生出力:

```text
62
```

## 手順4b: index.css の :root / :root.force-dark 外にある生hex

実行手法:

- `frontend/src/index.css` を走査し、`:root { ... }` と `:root.force-dark { ... }` のブロック外にある `#[0-9a-fA-F]{3,8}` を抽出
- 抽出結果を `/tmp/indexcss-outside-hex.txt` に保存

実行コマンド:

```bash
awk 'BEGIN{in_root=0; in_dark=0} /^:root[[:space:]]*\\{/ {in_root=1; next} /^:root\\.force-dark[[:space:]]*\\{/ {in_dark=1; next} in_root && /^}/ {in_root=0; next} in_dark && /^}/ {in_dark=0; next} (!in_root && !in_dark) && match($0, /#[0-9a-fA-F]{3,8}\\b/) { print FNR ":" $0 }' frontend/src/index.css | tee /tmp/indexcss-outside-hex.txt | wc -l
cut -d: -f1 /tmp/indexcss-outside-hex.txt | sort -n | uniq -c
cat /tmp/indexcss-outside-hex.txt
```

生出力:

```text
0
```

## 手順4c: TSX インラインスタイルの生hex

実行コマンド:

```bash
grep -rEn "#[0-9a-fA-F]{3,8}" frontend/src --include="*.tsx" --include="*.jsx" | grep -vE "frontend/src/(index|tokens)\.css" | tee /tmp/tsx-hex.txt | wc -l
```

生出力:

```text
38
```

## 補足

- 4a の対象は 62 件
- 4b の対象は 0 件
- 4c の対象は 38 件
