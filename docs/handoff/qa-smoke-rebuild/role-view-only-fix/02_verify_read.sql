SELECT p.id, p.key, p.category FROM ai_ro.tenant_001__role_permissions rp JOIN ai_ro.public__permissions p ON p.id = rp.permission_id WHERE rp.role_id = 2611 ORDER BY p.key;
