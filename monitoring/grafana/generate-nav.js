#!/usr/bin/env node
/**
 * monitoring/grafana/generate-nav.js
 * ===================================
 * nav-config.json を SSoT として全ダッシュボード JSON に
 * サイドバーナビゲーション付きヘッダーパネルを一括配布するスクリプト。
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

// ヘッダーテキストパネルの識別 ID（全ダッシュボード共通の予約 ID）
const HEADER_PANEL_ID = 9999;
// サイドバーナビ（8項目）を収容するために h=8 に拡張（旧: 3）
const HEADER_HEIGHT   = 8;

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

/**
 * Dashboard Links は空配列を返す。
 * ナビゲーションはヘッダーパネル内のサイドバー HTML に移行済み。
 */
const buildLinks = () => [];

/** パネル配列内の全パネルの y 座標を dy だけずらす（ネスト対応）*/
const shiftPanelsBy = (panels, dy) =>
  panels.map(p => ({
    ...p,
    gridPos: { ...p.gridPos, y: p.gridPos.y + dy },
    ...(p.panels && p.panels.length > 0
      ? { panels: shiftPanelsBy(p.panels, dy) }
      : {}),
  }));

/** 既存のヘッダーパネル（id=HEADER_PANEL_ID）を除去してから y を元に戻す */
const stripHeader = (panels) => {
  if (panels.length === 0 || panels[0].id !== HEADER_PANEL_ID) return panels;
  const headerHeight = panels[0].gridPos.h;
  return shiftPanelsBy(panels.slice(1), -headerHeight);
};

/**
 * サイドバーナビ付きヘッダーパネルの HTML を生成する。
 * アクティブなダッシュボード（currentUid）のナビ項目をハイライトする。
 */
const buildSidebarHtml = (header, currentUid) => {
  const baseStyle = [
    'display:flex',
    'align-items:center',
    'gap:8px',
    'padding:5px 10px',
    'text-decoration:none',
    'border-radius:4px',
    'font-size:12px',
    'line-height:1.4',
  ].join(';');

  const activeStyle   = 'color:#fff;background:rgba(255,152,0,0.28);font-weight:600';
  const inactiveStyle = 'color:rgba(204,204,220,0.75)';

  const navItems = navConfig.links.map(link => {
    const isActive = link.uid === currentUid;
    const style    = `${baseStyle};${isActive ? activeStyle : inactiveStyle}`;
    return `<a href="${link.url}" style="${style}">${link.icon}&nbsp;${link.title}</a>`;
  }).join('');

  return (
    `<div style="display:flex;height:100%;align-items:stretch;font-family:sans-serif;box-sizing:border-box">`
    + `<div style="width:154px;min-width:154px;display:flex;flex-direction:column;padding:6px 4px;gap:2px;border-right:1px solid rgba(204,204,220,0.12)">`
    + navItems
    + `</div>`
    + `<div style="flex:1;padding:8px 14px;display:flex;flex-direction:column;justify-content:center;overflow:hidden">`
    + `<p style="margin:0;font-size:18px;font-weight:700;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${header.title}</p>`
    + `<p style="margin:4px 0 0;font-size:10px;opacity:0.6;line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">${header.subtitle}</p>`
    + `</div>`
    + `</div>`
  );
};

/** サイドバー付きヘッダーパネルを生成して先頭に追加、既存パネルを HEADER_HEIGHT 分押し下げる */
const applyHeader = (panels, header, currentUid) => {
  const headerPanel = {
    id:      HEADER_PANEL_ID,
    type:    'text',
    title:   '',
    gridPos: { h: HEADER_HEIGHT, w: 24, x: 0, y: 0 },
    options: {
      mode:    'html',
      content: buildSidebarHtml(header, currentUid),
    },
    transparent: true,
  };
  return [headerPanel, ...shiftPanelsBy(panels, HEADER_HEIGHT)];
};

let hasError = false;

files.forEach(filePath => {
  const file      = path.basename(filePath);
  const dashboard = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const uid       = dashboard.uid || '';
  const config    = navConfig.dashboards[uid];

  // 既存ヘッダーを除去した素の panels
  const basePanels = stripHeader(dashboard.panels || []);

  // ヘッダー設定がある場合は注入、ない場合はそのまま
  const newPanels = config && config.header
    ? applyHeader(basePanels, config.header, uid)
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
