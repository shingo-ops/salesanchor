## 8. VPS・SSH

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| 鍵を指定しない → `salesanchor-claude` は ForceCommand で監視4コマンドのみ | `manual-only/id_ed25519`（prod1）は PO の明示承認が必須。カードに「どの機体・どの鍵」を書く | 本セッション実測・§6-3 |
| 頼んだコマンドと無関係な定型出力が返る | 即停止（監視出力にすり替わっている） | design-partner.md §279 |
| 識別名を Host 名と思い込む | `~/.ssh/config` の Host 名を実測 | DBSSOT-RECON-03（未検証） |
| Codex の `sleep 180` が30秒で打ち切られる | 長い待ちは分割する | MERGE-FIX-08（未検証） |

