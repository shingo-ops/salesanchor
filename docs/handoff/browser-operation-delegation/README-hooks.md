# chrome-op-guard（画面操作の見張り）置き場・取り付け・戻し方

設計の正本: [design.md](design.md) §4〜§8 / ADR-1085（Draft）/ 実装カード: [card-bin1.md](card-bin1.md)。便1は部屋 P だけ。

## 置き場

| 物 | 場所 |
|---|---|
| 見張り（PreToolUse） | `hooks/chrome_op_guard.py` |
| 住所の記録（PostToolUse） | `hooks/chrome_op_record.py` |
| 共有部品 | `hooks/chrome_common.py` |
| 区分の正本 | `hooks/tiers.json`（文書に書き写さない） |
| 同意票の1行を作る台本 | `chrome-consent-line.py` |
| 試験 | `scripts/dev/chrome-guard-tests.py`（T1〜T15・T17〜T19） |
| 週次点検 | `scripts/dev/consent-audit.py --audit` の「5. 画面操作」（G2〜G4） |

取り付け後の本物: `~/.claude/scripts/chrome-op-guard/`（4ファイル・権限 555）。同意の判定は取り付け済みの `~/.claude/scripts/consent_check.py` を使う。

## 取り付け・戻し（PO が `!` で実行）

```
bash docs/handoff/browser-operation-delegation/po-apply-chrome-guard.sh            # 初回（試験 → 反映 → T16 → 不合格なら自動で戻す）
bash docs/handoff/browser-operation-delegation/po-apply-chrome-guard.sh --update   # 中身が違うファイルだけ入れ替える
bash docs/handoff/browser-operation-delegation/po-rollback-chrome-guard.sh         # 登録2件を外し、置き場を消す
```

取り付けの直後に Opus が `tabs_context_mcp` を1回呼び、`~/.claude/logs/chrome-ops.jsonl` の `tab_context_parsed` が `true` であることを確かめる（T20）。`false` なら便1は合格にせず、rollback で戻して設計し直す。

## 同意票の1行

```
python3 docs/handoff/browser-operation-delegation/chrome-consent-line.py '<tool_input の JSON>' <道具の短い名>
```

出力をそのまま同意票の `操作N:` に書く（見張りが作る1行と同じ関数）。
