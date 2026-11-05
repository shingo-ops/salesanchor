本報告はカード card-impl-2 の実行結果である

開始 HEAD: b2c95ec9fd918c910eef06a88667536e6067a15d（b2c95ec9f で始まることを確認）／コード commit: 5208a1012a0a1bfdc6af607205c46eab80586751

## 差分の要約（9 ファイル）
- routers: discord_channel_invite=leads.discord_invite、discord_role_resync=leads.discord_resync、discord_remove の 3 本=remove_channel/kick/ban の各鍵
- services/tenant.py: マネージャーに 5 鍵、営業に invite・resync の 2 鍵（他の役割は無し）
- tests/conftest.py: ALL_TEST_PERMISSIONS に 5 鍵を追加
- tests/test_permission_catalog.py: _REASSIGNED_ROUTES から discord 2 行を削除、_DISCORD_ROUTES と test_discord_routes_require_own_keys（C6）を追加
- tests/test_system_roles.py: test_discord_keys_in_default_roles を追加
- InboxKartePanel.tsx: 招待・再同期・外す/Kick/BAN を新しい鍵で出し分け（DiscordRemoveButtons に canRemove/canKick/canBan）
- InboxKartePanel.discordButtons.test.tsx: T2/T3 を新しい鍵に書き直し、T4（it.each 5 通り）を追加

## 点検（生出力はファイルに保存、tail）
- pytest（python3.12 venv。ログ全体: pytest.log）: 最終 2 行
```
FAIL Required test coverage of 60% not reached. Total coverage: 29.52%
23 passed, 1 warning in 24.87s
```
  ※ 'FAIL Required test coverage of 60%' は 2 ファイルだけ流したためのカバレッジ閾値で、試験自体は 23 passed。
- vitest（tail）:
```

 Test Files  1 passed (1)
      Tests  8 passed (8)
   Start at  14:11:43
   Duration  2.53s (transform 923ms, setup 55ms, import 1.29s, tests 131ms, environment 847ms)

```
- tsc --noEmit: exit 2。エラー 4 件、InboxKarte を含むものは 0 件（src/api/generated/schema が無い等の既存の生成物不足）。tail:
```
src/features/tcg-sold-out/soldOutApi.ts(3,45): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/inventory/OwnInventoryPage.tsx(11,33): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,27): error TS7006: Parameter 'line' implicitly has an 'any' type.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,33): error TS7006: Parameter 'index' implicitly has an 'any' type.
```
- eslint: exit 0、出力なし
- git grep（routers/discord_*.py に旧 require_permission）: 0 件
- git diff origin/main...HEAD --name-only: docs/handoff/discord-buttons-permission/ 配下と上の 9 ファイルのみ

## 想定分岐
- 当たらなかった（行番号どおり、require_permission は各道に 1 つ、役割名一致、既存試験は落ちず）。
- tsc の既存エラーは生成物不足でありこのカードの範囲外。CI で判定する。

DONE
