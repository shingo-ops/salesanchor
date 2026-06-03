#!/usr/bin/env node
/**
 * monitoring/grafana/generate-nav.js
 * ===================================
 * nav-config.json を SSoT として全ダッシュボード JSON に
 * 左列サイドバーナビゲーションパネルを一括配布するスクリプト。
 *
 * 使い方:
 *   node monitoring/grafana/generate-nav.js          # 全ダッシュボードを更新
 *   node monitoring/grafana/generate-nav.js --check  # CI 整合性チェック（差分があれば exit 1）
 *
 * タブの追加・変更は nav-config.json だけ編集してこのスクリプトを実行する。
 * UX 階層（大→中→小）はパネルの links[] で定義。フォルダは管理用のみ。
 */

const fs   = require('fs');
const path = require('path');

const CHECK_MODE     = process.argv.includes('--check');
const NAV_CONFIG     = 'monitoring/grafana/nav-config.json';
const DASHBOARDS_DIR = 'monitoring/grafana/provisioning/dashboards/json';

// サイドバーパネルの識別 ID（全ダッシュボード共通の予約 ID）
const SIDEBAR_PANEL_ID = 9999;

// サイドバー幅（24列グリッドの列数）= 4 → 各ダッシュボードで 20列がコンテンツ領域になる
// 4列で 6→5, 12→10, 24→20 と整数に収まる
const SIDEBAR_WIDTH  = 4;
const CONTENT_COLS   = 24 - SIDEBAR_WIDTH; // 20

// 全ダッシュボード最大高さ(47)を超える値。サイドバーが全高をカバーする
const SIDEBAR_HEIGHT = 60;

const navConfig = JSON.parse(fs.readFileSync(NAV_CONFIG, 'utf8'));

/** DASHBOARDS_DIR 以下を再帰的に走査して *.json を返す */
const collectJsonFiles = (dir) => {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectJsonFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.json')) {
      results.push(fullPath);
    }
  }
  return results;
};

const files = collectJsonFiles(DASHBOARDS_DIR);

/** Dashboard Links は空配列（ナビはサイドバーパネルに移行） */
const buildLinks = () => [];

// ── パネル座標変換 ────────────────────────────────────────────────────────────

/** 旧ヘッダー（w=24）が残っている場合の y シフト戻し */
const shiftPanelsBy = (panels, dy) =>
  panels.map(p => ({
    ...p,
    gridPos: { ...p.gridPos, y: p.gridPos.y + dy },
    ...(p.panels && p.panels.length > 0
      ? { panels: shiftPanelsBy(p.panels, dy) }
      : {}),
  }));

/**
 * 24 列座標 → サイドバー右側の CONTENT_COLS 列座標に変換
 *   x: SIDEBAR_WIDTH + round(old_x * CONTENT_COLS / 24)
 *   w: round(old_w  * CONTENT_COLS / 24)
 * 検証:
 *   x=0,w=6  → x=4,w=5   (4列ブロック × 4 = 20 ✓)
 *   x=0,w=12 → x=4,w=10  (2列ブロック × 2 = 20 ✓)
 *   x=0,w=24 → x=4,w=20  (フル幅 ✓)
 */
const scalePanelToContent = (panel) => ({
  ...panel,
  gridPos: {
    ...panel.gridPos,
    x: SIDEBAR_WIDTH + Math.round(panel.gridPos.x * CONTENT_COLS / 24),
    w: Math.round(panel.gridPos.w * CONTENT_COLS / 24),
  },
  ...(panel.panels && panel.panels.length > 0
    ? { panels: panel.panels.map(scalePanelToContent) }
    : {}),
});

/**
 * CONTENT_COLS 列座標 → 元の 24 列座標に戻す（strip 用）
 */
const unscalePanelFromContent = (panel) => ({
  ...panel,
  gridPos: {
    ...panel.gridPos,
    x: Math.round((panel.gridPos.x - SIDEBAR_WIDTH) * 24 / CONTENT_COLS),
    w: Math.round(panel.gridPos.w * 24 / CONTENT_COLS),
  },
  ...(panel.panels && panel.panels.length > 0
    ? { panels: panel.panels.map(unscalePanelFromContent) }
    : {}),
});

/**
 * 既存のサイドバー/ヘッダーパネル（id=SIDEBAR_PANEL_ID）を除去して座標を元に戻す。
 * - w=24  → 旧「上部ヘッダー」形式: y を headerHeight 分戻す
 * - w<24  → 新「左列サイドバー」形式: x/w を 24列座標に戻す
 */
const stripNavPanel = (panels) => {
  if (panels.length === 0 || panels[0].id !== SIDEBAR_PANEL_ID) return panels;
  const first = panels[0];
  if (first.gridPos.w === 24) {
    // 旧ヘッダー形式 → y シフトを戻す
    return shiftPanelsBy(panels.slice(1), -first.gridPos.h);
  }
  // 新サイドバー形式 → x/w スケールを戻す
  return panels.slice(1).map(unscalePanelFromContent);
};

// ── HTML 生成 ─────────────────────────────────────────────────────────────────

/**
 * 左列サイドバーパネルの HTML を生成する。
 * - 上部: ダッシュボードタイトル
 * - 下部: ナビリンク（現在地をオレンジハイライト）
 */
const buildSidebarHtml = (header, currentUid) => {
  const itemBase = [
    'display:flex',
    'align-items:center',
    'gap:6px',
    'padding:5px 8px',
    'text-decoration:none',
    'border-radius:4px',
    'font-size:12px',
    'line-height:1.4',
    'white-space:nowrap',
    'overflow:hidden',
    'text-overflow:ellipsis',
  ].join(';');

  const navItems = navConfig.links.map(link => {
    const isActive = link.uid === currentUid;
    const style    = isActive
      ? `${itemBase};color:#fff;background:rgba(255,152,0,0.28);font-weight:600`
      : `${itemBase};color:rgba(204,204,220,0.75)`;
    return `<a href="${link.url}" style="${style}">${link.icon}&nbsp;${link.title}</a>`;
  }).join('');

  return (
    `<div style="display:flex;flex-direction:column;height:100%;font-family:sans-serif;box-sizing:border-box;padding:0">`
    + `<div style="padding:10px 8px 8px;border-bottom:1px solid rgba(204,204,220,0.12)">`
    + `<p style="margin:0;font-size:11px;font-weight:700;color:#fff;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${header.title}</p>`
    + `</div>`
    + `<div style="flex:1;padding:8px 4px;display:flex;flex-direction:column;gap:2px">`
    + navItems
    + `</div>`
    + `</div>`
  );
};

// ── レイアウト適用 ────────────────────────────────────────────────────────────

/**
 * 左列サイドバーを先頭に追加し、既存パネルを x 方向にスケールして右へ寄せる。
 */
const applySidebar = (panels, header, currentUid) => {
  const sidebarPanel = {
    id:          SIDEBAR_PANEL_ID,
    type:        'text',
    title:       '',
    gridPos:     { h: SIDEBAR_HEIGHT, w: SIDEBAR_WIDTH, x: 0, y: 0 },
    options:     { mode: 'html', content: buildSidebarHtml(header, currentUid) },
    transparent: true,
  };
  return [sidebarPanel, ...panels.map(scalePanelToContent)];
};

// ── メイン処理 ────────────────────────────────────────────────────────────────

let hasError = false;

files.forEach(filePath => {
  const file      = path.basename(filePath);
  const dashboard = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const uid       = dashboard.uid || '';
  const config    = navConfig.dashboards[uid];

  // 既存ナビパネル（旧ヘッダー or 旧サイドバー）を除去して素の panels に戻す
  const basePanels = stripNavPanel(dashboard.panels || []);

  // サイドバーを注入（config がない場合はそのまま）
  const newPanels = config && config.header
    ? applySidebar(basePanels, config.header, uid)
    : basePanels;

  const updated = {
    ...dashboard,
    links:  buildLinks(),
    panels: newPanels,
    ...(config ? { description: config.description } : {}),
  };

  const newContent = JSON.stringify(updated, null, 2) + '\n';
  const oldContent = fs.readFileSync(filePath, 'utf8');

  if (CHECK_MODE) {
    if (newContent !== oldContent) {
      console.error(`❌ ${file}: nav-config.json と同期されていません。node monitoring/grafana/generate-nav.js を実行してください。`);
      hasError = true;
    } else {
      console.log(`  ✅ ${file}: 同期済み`);
    }
  } else {
    fs.writeFileSync(filePath, newContent);
    console.log(`✅ ${file} 更新完了`);
  }
});

if (hasError) process.exit(1);
if (CHECK_MODE) console.log('\n✅ 全ダッシュボード nav-config.json と同期済み');
