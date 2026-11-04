# impl-report-2

## 開始時 HEAD
`git rev-parse HEAD` = bf390f433a130bd69860045d35431556c6405e25（期待どおり）

## 依存の入れ方
- python3.12 -m venv /tmp/venv312（py312-guard のため）
- /tmp/venv312/bin/pip install -r requirements.txt
- /tmp/venv312/bin/pip install pytest pytest-asyncio httpx aiosqlite pytest-xdist pytest-cov（requirements に無く、conftest/pyproject が要求）

## git diff origin/release/permission-keys-conditions-code（変更前の生出力）
```diff
diff --git a/backend/tests/test_conditions_permission_keys.py b/backend/tests/test_conditions_permission_keys.py
index 9090cba72..6d6dd767f 100644
--- a/backend/tests/test_conditions_permission_keys.py
+++ b/backend/tests/test_conditions_permission_keys.py
@@ -2,7 +2,11 @@
 
 from __future__ import annotations
 
-from app.main import app
+
+def _app():
+    from app.main import app
+
+    return app
 
 ALLOWED_KEYS = {
     "conditions.view",
@@ -25,7 +29,7 @@ def _key_sets(route) -> list[set[str]]:
 
 
 def _find(method: str, path: str):
-    for route in app.routes:
+    for route in _app().routes:
         if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
             return route
     raise AssertionError(f"route not found: {method} {path}")
@@ -55,7 +59,7 @@ def test_catalog_requires_conditions_view():
 
 def test_all_keys_on_conditions_and_categories_routes_are_known():
     checked = 0
-    for route in app.routes:
+    for route in _app().routes:
         path = getattr(route, "path", "")
         if not (path.startswith("/api/v1/conditions") or path.startswith("/api/v1/product-categories")):
             continue
```

## 順 A（keys, inventory, import）tail -30
```
app/tasks/maintenance.py                               179    179     0%   11-449
app/tasks/master_required_fields_monitor.py             45     45     0%   7-93
app/tasks/ops_mail_monitor.py                           14     14     0%   1-34
app/tasks/priority_scoring_check.py                     81     81     0%   18-193
app/tasks/refresh_meta_tokens.py                       156    156     0%   45-481
app/tasks/reports.py                                    42     42     0%   19-228
app/tasks/review_mail_monitor.py                        17     17     0%   1-38
app/tasks/rule_test.py                                  49     49     0%   9-141
app/tasks/sa02_recon_monitor.py                         70     70     0%   1-148
app/tasks/tcg_extraction.py                            358    291    19%   69, 98, 121-134, 138-145, 157-169, 189-228, 236, 269-315, 324-330, 337-434, 447-461, 470-487, 497-642, 662-666, 682-684, 692-
app/tasks/tcg_extraction_recovery.py                   189    189     0%   23-587
app/tasks/tcg_import_discard.py                         22     22     0%   10-64
app/tasks/tcg_mirror.py                                114    114     0%   17-338
app/tasks/translation.py                                62     62     0%   1-177
app/tasks/verify_meta_subscriptions.py                 126    126     0%   41-360
app/tasks/viewer_inventory_cache.py                     81     57    30%   40-45, 50-69, 74-99, 104-134, 139-142
app/tasks/viewer_share_flag_monitor.py                  63     63     0%   7-96
app/tcg_config.py                                        8      8     0%   15-29
app/tools/__init__.py                                    0      0   100%
app/tools/prompt_ab.py                                 438    438     0%   20-727
app/tools/prompt_ab_recompute.py                        97     97     0%   11-147
app/tools/reextract_v6_with_v102.py                    562    562     0%   27-852
app/tools/sync_review_reason_labels.py                  15     15     0%   8-31
app/viewer_admin_cli.py                                 30     30     0%   6-53
app/viewer_discord_cli.py                               85     85     0%   6-141
app/viewer_register_cli.py                              19     19     0%   6-30
----------------------------------------------------------------------------------
TOTAL                                                45934  32235    30%
FAIL Required test coverage of 60% not reached. Total coverage: 29.82%
27 passed, 3 warnings in 36.83s
```

## 順 B（inventory, import, keys）tail -30
```
app/tasks/maintenance.py                               179    179     0%   11-449
app/tasks/master_required_fields_monitor.py             45     45     0%   7-93
app/tasks/ops_mail_monitor.py                           14     14     0%   1-34
app/tasks/priority_scoring_check.py                     81     81     0%   18-193
app/tasks/refresh_meta_tokens.py                       156    156     0%   45-481
app/tasks/reports.py                                    42     42     0%   19-228
app/tasks/review_mail_monitor.py                        17     17     0%   1-38
app/tasks/rule_test.py                                  49     49     0%   9-141
app/tasks/sa02_recon_monitor.py                         70     70     0%   1-148
app/tasks/tcg_extraction.py                            358    291    19%   69, 98, 121-134, 138-145, 157-169, 189-228, 236, 269-315, 324-330, 337-434, 447-461, 470-487, 497-642, 662-666, 682-684, 692-
app/tasks/tcg_extraction_recovery.py                   189    189     0%   23-587
app/tasks/tcg_import_discard.py                         22     22     0%   10-64
app/tasks/tcg_mirror.py                                114    114     0%   17-338
app/tasks/translation.py                                62     62     0%   1-177
app/tasks/verify_meta_subscriptions.py                 126    126     0%   41-360
app/tasks/viewer_inventory_cache.py                     81     57    30%   40-45, 50-69, 74-99, 104-134, 139-142
app/tasks/viewer_share_flag_monitor.py                  63     63     0%   7-96
app/tcg_config.py                                        8      8     0%   15-29
app/tools/__init__.py                                    0      0   100%
app/tools/prompt_ab.py                                 438    438     0%   20-727
app/tools/prompt_ab_recompute.py                        97     97     0%   11-147
app/tools/reextract_v6_with_v102.py                    562    562     0%   27-852
app/tools/sync_review_reason_labels.py                  15     15     0%   8-31
app/viewer_admin_cli.py                                 30     30     0%   6-53
app/viewer_discord_cli.py                               85     85     0%   6-141
app/viewer_register_cli.py                              19     19     0%   6-30
----------------------------------------------------------------------------------
TOTAL                                                45934  32235    30%
FAIL Required test coverage of 60% not reached. Total coverage: 29.82%
27 passed, 3 warnings in 35.13s
```

注: 両回とも 27 passed。末尾の coverage 60% 未達は一部ファイルだけ流したための pyproject 既定の閾値で、試験の失敗ではない。行は幅200で切って記録。
