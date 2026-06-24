# design — send-guard-phase-a

**仕事名**: send-guard-phase-a
**日付**: 2026-06-24
**対象ADR**: ADR-143
**担当**: Hikky-dev (Claude Code)
**recon参照**: docs/handoff/send-guard-phase-a/recon.md

---

## 背景・目的

ADR-143 に基づき、担当者が日本語（かな文字）を含む下書きを英語圏受信者に誤送信する事故を防ぐ。
バックエンド変更ゼロ・フロントエンドのみで Phase A を実装。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `auto` + かな → ダイアログ表示 | Playwright QA-1-1: `.send-guard-dialog` が visible |
| `auto` + 英語のみ → 直送（ダイアログなし） | Playwright QA-1-2: `sendCalled=true` + dialog not visible |
| `ja`（手動）+ かな → ダイアログなし・直送 | Playwright QA-1-3: `sendCalled=true` + dialog not visible |
| `ja`（手動）+ 英語のみ → ダイアログなし | Playwright QA-1-4 |
| `en`（手動）+ かな → ダイアログ表示 | Playwright QA-1-5: `.send-guard-dialog` が visible |
| `en`（手動）+ 英語のみ → ダイアログなし | Playwright QA-1-6 |
| IME 変換中 Enter → 送信・ダイアログとも不発 | Playwright QA-2-1: `isComposing=true` Enter でダイアログなし |
| `compositionend` 後 Enter + かな → ダイアログ | Playwright QA-2-2 |
| トグル3ボタン（auto/ja/en）描画 + デフォルト auto active | Playwright QA-3-1 |
| スレッドごとに言語設定が独立保持される | Playwright QA-5: A=en→B=auto→A=en 記憶 |
| バックエンドファイル無変更 | `git diff develop -- backend/` が空 |
| `migrations/` 変更ゼロ | `git diff develop -- migrations/` が空 |

---

## 実装方針

### かな判定

```
/[\u3040-\u30FF]/  — 平仮名 U+3040-U+309F + 片仮名 U+30A0-U+30FF
```

### 発火条件

```
shouldFireGuard = draftHasKana && recipientLanguageSetting !== "ja"
```

### スレッド独立

`languageOverrideByLead: Record<number, "auto"|"ja"|"en">` を `useInboxState` に持ち、lead_id をキーに独立管理。

### IME Enter 誤爆防止

`handleKeyDownGuarded` で `e.nativeEvent.isComposing` が `true` の場合は `checkAndSend` を呼ばない。

---

## 外部・過去事例の参照と我々への応用

ADR-110 で確立した「自動送信永久禁止原則」を Phase A に継承。
かな検出によるシンプルなガードは、多数決判定（Phase B）のデータ蓄積前でもゼロコスト・バックエンド変更なしで保護できる。
「シンプルに先行保護 → データ蓄積後に高精度化」パターンは段階的リリースのベストプラクティス。
