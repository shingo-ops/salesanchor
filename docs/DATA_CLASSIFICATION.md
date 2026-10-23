# データ分類ポリシー - Sales Anchor

## 1. データ分類レベル

| レベル | 定義 | 例 | 取扱い |
|--------|------|-----|--------|
| 機密 (Confidential) | 漏洩時に重大な損害 | パスワードハッシュ、APIキー、Firebase認証情報 | 暗号化保存、アクセスログ必須、最小権限 |
| 社外秘 (Internal) | 社内限定の業務データ | 顧客情報、商談金額、注文データ | テナント分離、認証必須、監査ログ |
| 公開 (Public) | 漏洩しても影響なし | ヘルスチェック応答、APIバージョン | 制限なし |

## 2. データ種別と分類

### テナントデータ（社外秘）
| データ | テーブル | 保護手段 |
|--------|---------|---------|
| 顧客名・連絡先 | companies（ADR-089） | スキーマ分離 + RLS |
| 商談情報・金額 | deals | スキーマ分離 + RLS |
| 注文情報 | orders | スキーマ分離 + RLS |
| 操作履歴 | audit_logs | スキーマ分離 + RLS |

### 認証データ（機密）
| データ | テーブル/場所 | 保護手段 |
|--------|-------------|---------|
| パスワード | users.password_argon2_hash（自社ログインとパスワード再設定。再設定は AUTH_PROVIDER に関係なく動く: backend/app/routers/auth.py:350,468）／viewer_accounts.password_argon2_hash（閲覧ページ: migrations/20261016_150000_add_viewer_accounts.sql:12） | Argon2id（backend/app/auth/passwords.py）。ログイン判定の既定は Firebase（self_tokens.py:20）。bcrypt（12ラウンド）は bot の API キー（backend/app/routers/bots.py:58）だけ。本番に行があるかはまだ確かめていない |
| Firebase IDトークン | メモリ/Redis | TTL付きキャッシュ、ブラックリスト |
| Firebase認証情報 | firebase-credentials.json | ファイル権限600、.gitignore |

### インフラデータ（機密）
| データ | 場所 | 保護手段 |
|--------|------|---------|
| DBパスワード | .env | .gitignore、ファイル権限 |
| Redisパスワード | .env | .gitignore、ファイル権限 |
| SSHキー | GitHub Secrets | GitHub暗号化保存 |
| SSL証明書 | certbot/conf | ファイル権限、自動更新 |

## 3. データ保持ルール

| データ種別 | 保持期間 | 削除方法 |
|-----------|---------|---------|
| 監査ログ | 90日 | Celery定期タスクで自動削除 |
| DBバックアップ | 30日 | シェルスクリプトで自動ローテーション |
| 認証イベントログ | 90日 | 同上 |
| 顧客・商談データ | テナント契約期間中 | テナント退会時に全スキーマ削除 |
| Redis キャッシュ | 最大11分（KPI）/ 5分（JWT） | TTLで自動期限切れ |

## 4. データ処理の原則

1. **最小権限**: データへのアクセスは業務上必要な範囲に限定
2. **暗号化**: 通信はTLS 1.2+、DB に置くパスワードは Argon2id（users.password_argon2_hash と viewer_accounts.password_argon2_hash。ログイン判定の既定は Firebase。bcrypt は bot の API キーだけ。本番に行があるかはまだ確かめていない）
3. **監査可能性**: 全データ変更に監査ログを記録
4. **テナント分離**: テナント間のデータは物理的にスキーマ分離
5. **安全な削除**: バックアップも含め保持期間後に確実に削除
