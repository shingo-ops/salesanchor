/* progress.js — 進捗バッジを progress.json から動的レンダリング
 * デプロイ時に生成された progress.json を fetch してバッジと進捗バーを更新する。
 * 取得失敗時は静的フォールバック表示のまま（サイト全体は壊れない）。
 */

const PHASE_LABEL = {
  0: '未着手',
  1: '① KGI承認',
  2: '② recon完了',
  3: '③ 設計確定',
  4: '④ 実装中',
  5: '⑤ 本番反映済み',
  6: '⑥ KGI実測達成',
};

function badgeClass(pct) {
  if (pct === null) return 'badge--cross';
  if (pct === 0)    return 'badge--todo';
  if (pct < 90)     return 'badge--wip';
  return 'badge--done';
}

function badgeText(item) {
  if (item.progress === null) return '横断適用';
  if (item.progress === 0)    return '未着手';
  if (item.progress >= 90)    return '完了';
  const phase = PHASE_LABEL[item.phase] || '';
  return phase ? `${phase} (${item.progress}%)` : `進行中 ${item.progress}%`;
}

async function loadProgress() {
  let data;
  try {
    const resp = await fetch('/design/progress.json');
    if (!resp.ok) return;
    data = await resp.json();
  } catch (_) {
    return; // graceful degradation
  }

  if (!Array.isArray(data.items)) return;

  data.items.forEach(function(item) {
    const card = document.querySelector('[data-sa="' + item.id + '"]');
    if (!card) return;

    // バッジ更新
    const badge = card.querySelector('.badge');
    if (badge) {
      badge.textContent = badgeText(item);
      badge.className = 'badge ' + badgeClass(item.progress);
    }

    // 進捗バー更新
    const bar = card.querySelector('.progress-bar-inner');
    if (bar && item.progress !== null) {
      bar.style.width = item.progress + '%';
    }

    // フェーズ表示更新
    const phaseEl = card.querySelector('.sa-card__phase');
    if (phaseEl && item.phase_label) {
      phaseEl.textContent = item.phase_label;
    }
  });

  // 生成日時を表示
  const tsEl = document.getElementById('progress-generated-at');
  if (tsEl && data.generated_at) {
    const d = new Date(data.generated_at);
    tsEl.textContent = d.toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' }) + ' 生成';
  }
}

document.addEventListener('DOMContentLoaded', loadProgress);
