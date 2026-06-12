/* progress.js — 進捗バッジ・フェーズ・次アクションを progress.json から動的レンダリング
 * デプロイ時に生成された progress.json を fetch してバッジ・進捗バー・フェーズ・次アクションを更新する。
 * 取得失敗時は静的フォールバック表示のまま（サイト全体は壊れない）。
 *
 * progress.json の items 配列要素（generate-progress-json.py が出力する正規化フィールド）:
 *   id          : "SA-01" 〜 "SA-12"
 *   progress    : 0〜100 の整数 or null（横断適用は null）
 *   phase       : 0〜6 の整数 or null
 *   phase_label : "④ 実装中（...）" などの文字列
 *   next_action : "PR マージ → 本番反映" などの文字列
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
  const phaseNum = item.phase;
  const phaseStr = (phaseNum !== null && PHASE_LABEL[phaseNum]) ? PHASE_LABEL[phaseNum] : '';
  return phaseStr ? `${phaseStr} (${item.progress}%)` : `進行中 ${item.progress}%`;
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

    // フェーズ表示更新（短縮ラベルを使う）
    const phaseEl = card.querySelector('.sa-card__phase');
    if (phaseEl) {
      if (item.phase_label) {
        const shortLabel = (item.phase !== null && PHASE_LABEL[item.phase])
          ? PHASE_LABEL[item.phase]
          : item.phase_label;
        phaseEl.textContent = shortLabel;
        phaseEl.style.display = '';
      } else {
        phaseEl.style.display = 'none';
      }
    }

    // 次のアクション更新
    const nextEl = card.querySelector('.sa-card__next');
    if (nextEl) {
      if (item.next_action) {
        nextEl.textContent = '次: ' + item.next_action;
        nextEl.style.display = '';
      } else {
        nextEl.style.display = 'none';
      }
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
