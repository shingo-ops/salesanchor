# Fable 審査記録: Colima 使い終わり自動停止（2026-10-15）

生の審査文: /tmp/CC報告ファイル/ac-heavy/docker-idle/review-design1.md・review-design2.md・review-design3.md・review-code1.md・review-code2.md（Mac 上の作業記録）。

| 回 | 対象 | 判定 | 主な指摘と対応 |
|---|---|---|---|
| 設計1 | design v1 | REVISE | MEDIUM-1 見回りごとの fetch/checkout が janitor と取り合う→読み取りだけに変更／MEDIUM-2 判定順と0件の扱い→順序固定・逐次化／MEDIUM-3 VM 再起動時に古い記録で止める恐れ→ha.pid で同一性確認／MEDIUM-4 ロックの stale 処理→pid 生存確認／MEDIUM-5 区分・仕様書・ADR の明記→区分 A・仕様書対象外・ADR 変更なしを記載／LOW-6〜10 KGI 60分・K2/K5 の○×化・launchd 環境での dry-run・recon にコマンド全文 |
| 設計2 | design v2 | REVISE | HIGH-1 HEAD と origin/main の完全一致は実機でほぼ成立しない→`merge-base --is-ancestor` に変更／LOW-11 pgrep に docker-compose・logs・up を追加／LOW-12 janitor 実行中は exit 0 で見送り／仕様書対象外の判断を PO に明示 |
| 設計3 | design v2.1 | APPROVE | 残る LOW は Generator 申し送り（引用符・ロック pid の書き込み位置・.err 文言の区別を手順書に1行） |
| コード1 | commit 1b9963199 | REVISE | MEDIUM-1 試験 T8（1799 秒）が秒境界で稀に失敗→1790 秒に変更（本体は変更なし）。他は設計と全項目一致 |
| コード2 | commit d08d4fdc3 | APPROVE | T8 を 1790 秒に変更。本体・plist・手順書は差分なし。/bin/bash 3.2 で5回＋10回連続 FAIL=0。残る指摘なし |
