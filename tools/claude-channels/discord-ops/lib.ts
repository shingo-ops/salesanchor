/**
 * discord-ops: pure decision logic (P1 / P3 / P6 / P8 / P9).
 * No Discord or MCP imports here so that `bun test` can cover it directly.
 */
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs'
import { join } from 'path'

export type MonitorChannels = Record<string, { allowWebhooks: string[] }>

export type OpsAccess = {
  allowFrom?: string[]
  monitorChannels?: MonitorChannels
  opsChannel?: string
}

export const MAX_BODY_CHARS = 4000
export const PROPOSAL_ID_RE = /^[A-Za-z0-9_-]{1,60}$/

// ---- P1: which webhook posts are delivered as alerts ----------------------

export type WebhookInfo = {
  webhookId: string
  channelId: string
  /** Parent channel id when the message is inside a thread. */
  parentId?: string | null
  isThread: boolean
}

/** Only a webhook listed for the (parent) monitor channel is delivered. */
export function webhookVerdict(access: OpsAccess, info: WebhookInfo): 'deliver' | 'drop' {
  const monitorKey = info.isThread ? info.parentId ?? info.channelId : info.channelId
  const allowed = access.monitorChannels?.[monitorKey]?.allowWebhooks
  if (!allowed || !info.webhookId) return 'drop'
  return allowed.includes(info.webhookId) ? 'deliver' : 'drop'
}

// ---- P3: notification body -------------------------------------------------

export type EmbedLike = {
  title?: string | null
  description?: string | null
  fields?: ReadonlyArray<{ name: string; value: string }> | null
}

/** content + embed title / description / "name: value" fields, newline-joined, capped. */
export function buildBody(content: string | null | undefined, embeds: ReadonlyArray<EmbedLike> = []): string {
  const parts: string[] = []
  if (content) parts.push(content)
  for (const e of embeds) {
    if (e.title) parts.push(e.title)
    if (e.description) parts.push(e.description)
    for (const f of e.fields ?? []) parts.push(`${f.name}: ${f.value}`)
  }
  return parts.join('\n').slice(0, MAX_BODY_CHARS)
}

// ---- P6: outbound target gate ---------------------------------------------

export type ReplyTarget = {
  type: 'dm' | 'guild'
  channelId: string
  parentId?: string | null
  isThread: boolean
}

/** DM, the ops channel itself, or a thread whose parent is the ops channel. */
export function isAllowedReplyTarget(access: OpsAccess, target: ReplyTarget): boolean {
  if (target.type === 'dm') return true
  const ops = access.opsChannel
  if (!ops) return false
  const key = target.isThread ? target.parentId ?? target.channelId : target.channelId
  return key === ops
}

// ---- P9: alert title classification ---------------------------------------

export function classifyAlertTitle(title: string): 'firing' | 'resolved' | 'other' {
  if (title.startsWith('[FIRING')) return 'firing'
  if (title.startsWith('[RESOLVED]')) return 'resolved'
  return 'other'
}

// ---- P8: proposals ---------------------------------------------------------

export type Proposal = {
  proposal_id: string
  thread_id: string
  summary: string
  action: string
  message_id: string
}

function assertProposalId(id: string): void {
  if (!PROPOSAL_ID_RE.test(id)) throw new Error('proposal_id must match [A-Za-z0-9_-]{1,60}')
}

/** Writes dir/<proposal_id>.json (mode 600). Throws on bad id or when it already exists. */
export function saveProposal(dir: string, proposal: Proposal): void {
  assertProposalId(proposal.proposal_id)
  mkdirSync(dir, { recursive: true, mode: 0o700 })
  const file = join(dir, `${proposal.proposal_id}.json`)
  if (existsSync(file)) throw new Error(`proposal ${proposal.proposal_id} already exists`)
  // flag 'wx' = fail if the file appeared between the check and the write.
  writeFileSync(file, JSON.stringify(proposal, null, 2) + '\n', { mode: 0o600, flag: 'wx' })
  chmodSync(file, 0o600)
}

/** Returns null for a bad id, a missing file, or unreadable / malformed content. */
export function loadProposal(dir: string, id: string): Proposal | null {
  if (!PROPOSAL_ID_RE.test(id)) return null
  try {
    const p = JSON.parse(readFileSync(join(dir, `${id}.json`), 'utf8')) as Partial<Proposal>
    if (
      p.proposal_id !== id ||
      typeof p.thread_id !== 'string' ||
      typeof p.summary !== 'string' ||
      typeof p.action !== 'string' ||
      typeof p.message_id !== 'string'
    ) {
      return null
    }
    return p as Proposal
  } catch {
    return null
  }
}

export type Decision = 'approve' | 'reject' | 'revise'

export function decisionNotification(
  proposal: Proposal,
  decision: Decision,
  userId: string,
): { content: string; meta: Record<string, string> } {
  const head = `decision ${decision} for proposal ${proposal.proposal_id}`
  const content =
    decision === 'approve'
      ? `${head}\n\n--- action (PO が承認した原文) ---\n${proposal.action}`
      : head
  return {
    content,
    meta: {
      kind: 'decision',
      proposal_id: proposal.proposal_id,
      decision,
      thread_id: proposal.thread_id,
      user_id: userId,
    },
  }
}

/** Body shown in Discord for a proposal: summary, then the exact action in a code block. */
export function proposalText(summary: string, action: string): string {
  return `${summary}\n\n**実行する操作（承認するとこの原文だけが実行されます）**\n\`\`\`\n${action}\n\`\`\``
}
