# recon — review-mail-discord-mention

**仕事名**: review-mail-discord-mention
**日付**: 2026-06-15
**対象ADR**: ADR-091
**担当**: Hikky-dev

---

## ADR 検索結果

- `git grep -i "imap\|review_mail\|mail.notif" docs/adr/` → 0件（レビューメール専用ADRなし）
- docs/adr/FEATURE-INDEX.md 参照 → Discord 関連は ADR-091（Discord Bot スコープ定義）
- Discord webhook 通知は ADR-091 スコープに含まれるため ADR-091 を対象ADRとして参照

---

## ファイル確認

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/services/review_mail_notifier.py:42` | _DISCORD_WEBHOOK env var 読み込み確認 |
| `backend/app/services/review_mail_notifier.py:95` | _build_discord_content 関数シグネチャ（mention 引数追加対象） |
| `backend/app/services/review_mail_notifier.py:109` | _post_discord 関数シグネチャ（allowed_mentions 追加対象） |
| `backend/app/services/review_mail_notifier.py:161` | check_and_notify エントリポイント（_parse_mention 呼び出し追加対象） |
| `backend/tests/test_review_mail_notifier.py:1` | テストファイル存在確認（拡張対象） |
| `docker-compose.yml:195` | REVIEW_MAIL_DISCORD_WEBHOOK env var 末尾（MENTION 追加対象） |
| `.env.example:111` | REVIEW_MAIL_DISCORD_WEBHOOK 直下（MENTION placeholder 追加対象） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Discord allowed_mentions フォーマット | Discord API docs 確認: parse:[] + users/roles リスト | ✅ 解消済み |
| 2 | ニックネームメンション形式の扱い | regex で type グループ判定し users リストで処理 | ✅ 解消済み |
| 3 | deploy.yml 変更不要か | MENTION 値は VPS .env 手動設定（GitHub Secret 不要） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- REVIEW_MAIL_DISCORD_MENTION の本番値は VPS .env に手動設定（deploy.yml 変更不要）
- 不正形式は warning ログのみ → メンションなしで通常通知（本体を止めない設計を継承）
- allowed_mentions の parse:[] により、件名・差出人由来の誤発火を防止
