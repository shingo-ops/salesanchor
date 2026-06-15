# Phase 3 設計 — review-mail-discord-mention

**対象ADR**: ADR-091
**recon**: docs/handoff/review-mail-discord-mention/recon.md
**日付**: 2026-06-15
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

Discord webhook の allowed_mentions フィールドは Discord 公式 API で規定されており、
parse: [] を設定することで message content 内の @everyone 等を誤発火させない標準的な手法。
Sales Anchor 既存の discord_notifier.py（ADR-091スコープ）では allowed_mentions 未使用だが、
件名・差出人がユーザー入力由来のレビューメール通知では必須の安全措置として追加する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| REVIEW_MAIL_DISCORD_MENTION 設定時、通知先頭にメンションが付く | pytest: TestCheckAndNotifyMention::test_mention_prepended_in_discord_payload |
| Discord POST payload に allowed_mentions が含まれる | pytest: TestPostDiscordAllowedMentions::test_allowed_mentions_in_payload |
| 不正形式は WARNING ログ + メンションなし送信 | pytest: TestCheckAndNotifyMention::test_invalid_mention_env_skips_mention |
| 未設定時は parse:[] のみ（誤発火なし）| pytest: TestPostDiscordAllowedMentions::test_default_allowed_mentions_parse_empty |
| ロールメンション形式が正しくパースされる | pytest: TestParseMention::test_role_mention_valid |
| 既存テスト 23 件が引き続き PASS | pytest tests/test_review_mail_notifier.py (39 tests) |

---

## 技術 How・KPI

- KPI: Discord 通知先頭にメンションが付くことで担当者が 5 分以内に気づける
- _parse_mention 関数: 正規表現で user / role メンション形式を厳格検証
  - user/nickname: users リストで処理
  - role: roles リストで処理
  - 不正形式: (None, parse:[]) を返し警告ログ
- _build_discord_content: mention 引数追加（None 時はプレフィックスなし）
- _post_discord: allowed_mentions 引数追加（None 時は parse:[] デフォルト）
- deploy.yml 変更なし（VPS .env 手動設定のみ）

---

## 弊害・トレードオフ

- メンション文字列追加で Discord 文字数制限 1800 字を圧迫するが、メンションは高々 23 文字のため実用上問題なし
- _parse_mention はモジュール変数を参照するため、実行中の env 変更は反映されない。Celery Beat 運用では再起動まで固定のため許容

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md / design.md 作成 | Hikky-dev |
| 2 | review_mail_notifier.py 修正 | Hikky-dev |
| 3 | test_review_mail_notifier.py 拡張（16 件追加） | Hikky-dev |
| 4 | docker-compose.yml 更新 | Hikky-dev |
| 5 | .env.example 更新 | Hikky-dev |
| 6 | 39 tests PASS 確認 | Hikky-dev |
| 7 | PR 作成（shingo-cc 名義） | Hikky-dev |

---

## 継続

- 完了後: VPS .env に REVIEW_MAIL_DISCORD_MENTION=<@1255555836776939692> 追記 → celery-worker/beat 再起動 → テストメールで動作確認
- 次フェーズへの引き継ぎ: なし（単機能追加・完結）
