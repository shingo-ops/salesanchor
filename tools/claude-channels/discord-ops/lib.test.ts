import { describe, expect, test } from 'bun:test'
import { mkdtempSync, statSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import {
  buildBody,
  classifyAlertTitle,
  decisionNotification,
  isAllowedReplyTarget,
  loadProposal,
  saveProposal,
  webhookVerdict,
  type OpsAccess,
  type Proposal,
} from './lib'

const MON = '1527986848490717245'
const WH = '1528064418448146552'
const OPS = '9000000000000000001'

const access: OpsAccess = {
  monitorChannels: { [MON]: { allowWebhooks: [WH] } },
  opsChannel: OPS,
}

describe('webhookVerdict', () => {
  test('delivers an allowed webhook in a monitor channel', () => {
    expect(webhookVerdict(access, { webhookId: WH, channelId: MON, isThread: false })).toBe('deliver')
  })
  test('drops a webhook that is not on the allow list', () => {
    expect(webhookVerdict(access, { webhookId: '111', channelId: MON, isThread: false })).toBe('drop')
  })
  test('drops a post in an unregistered channel', () => {
    expect(webhookVerdict(access, { webhookId: WH, channelId: '222', isThread: false })).toBe('drop')
  })
  test('judges a thread by its parent channel id', () => {
    expect(webhookVerdict(access, { webhookId: WH, channelId: 'thread1', parentId: MON, isThread: true })).toBe('deliver')
    expect(webhookVerdict(access, { webhookId: WH, channelId: MON, parentId: '222', isThread: true })).toBe('drop')
  })
  test('drops a post with an empty webhook id (bot that is not a webhook)', () => {
    expect(webhookVerdict(access, { webhookId: '', channelId: MON, isThread: false })).toBe('drop')
  })
  test('drops everything when monitorChannels is undefined', () => {
    expect(webhookVerdict({}, { webhookId: WH, channelId: MON, isThread: false })).toBe('drop')
  })
})

describe('buildBody', () => {
  test('uses content only when there are no embeds', () => {
    expect(buildBody('hello', [])).toBe('hello')
  })
  test('joins embed title, description and fields', () => {
    const body = buildBody('', [
      { title: '[FIRING:1] X', description: 'desc', fields: [{ name: 'instance', value: 'prod1' }] },
    ])
    expect(body).toBe('[FIRING:1] X\ndesc\ninstance: prod1')
  })
  test('cuts at 4000 characters', () => {
    expect(buildBody('a'.repeat(5000), []).length).toBe(4000)
  })
})

describe('isAllowedReplyTarget', () => {
  test('allows a DM', () => {
    expect(isAllowedReplyTarget(access, { type: 'dm', channelId: 'dm1', isThread: false })).toBe(true)
  })
  test('allows the ops channel itself', () => {
    expect(isAllowedReplyTarget(access, { type: 'guild', channelId: OPS, isThread: false })).toBe(true)
  })
  test('allows a thread whose parent is the ops channel', () => {
    expect(isAllowedReplyTarget(access, { type: 'guild', channelId: 't1', parentId: OPS, isThread: true })).toBe(true)
  })
  test('rejects a monitor channel', () => {
    expect(isAllowedReplyTarget(access, { type: 'guild', channelId: MON, isThread: false })).toBe(false)
  })
  test('rejects a thread whose parent is another channel', () => {
    expect(isAllowedReplyTarget(access, { type: 'guild', channelId: 't1', parentId: MON, isThread: true })).toBe(false)
  })
  test('rejects every guild channel when opsChannel is unset', () => {
    expect(isAllowedReplyTarget({}, { type: 'guild', channelId: OPS, isThread: false })).toBe(false)
  })
})

describe('classifyAlertTitle', () => {
  test('firing', () => expect(classifyAlertTitle('[FIRING:1] X')).toBe('firing'))
  test('resolved', () => expect(classifyAlertTitle('[RESOLVED] X')).toBe('resolved'))
  test('other', () => expect(classifyAlertTitle('⏰ tasks/todo.md に未更新タスク')).toBe('other'))
})

const sample: Proposal = {
  proposal_id: 'prod2-mem-1',
  thread_id: '555',
  summary: 'メモリ解放',
  action: 'docker compose restart backend',
  message_id: '777',
}

describe('saveProposal / loadProposal', () => {
  const fresh = () => mkdtempSync(join(tmpdir(), 'proposals-'))

  test('round-trips a saved proposal', () => {
    const dir = fresh()
    saveProposal(dir, sample)
    expect(loadProposal(dir, sample.proposal_id)).toEqual(sample)
  })
  test('throws when the same id is saved twice', () => {
    const dir = fresh()
    saveProposal(dir, sample)
    expect(() => saveProposal(dir, sample)).toThrow()
  })
  test('throws for an invalid id', () => {
    const dir = fresh()
    expect(() => saveProposal(dir, { ...sample, proposal_id: '../evil' })).toThrow()
    expect(() => saveProposal(dir, { ...sample, proposal_id: 'a'.repeat(61) })).toThrow()
  })
  test('writes the file with mode 600', () => {
    const dir = fresh()
    saveProposal(dir, sample)
    expect(statSync(join(dir, `${sample.proposal_id}.json`)).mode & 0o777).toBe(0o600)
  })
  test('returns null for an unknown or invalid id', () => {
    const dir = fresh()
    expect(loadProposal(dir, 'nope')).toBeNull()
    expect(loadProposal(dir, '../x')).toBeNull()
  })
})

describe('decisionNotification', () => {
  test('approve includes the original action text', () => {
    const n = decisionNotification(sample, 'approve', 'u1')
    expect(n.content).toContain('decision approve for proposal prod2-mem-1')
    expect(n.content).toContain('--- action (PO が承認した原文) ---')
    expect(n.content).toContain(sample.action)
  })
  test('reject does not include the action', () => {
    const n = decisionNotification(sample, 'reject', 'u1')
    expect(n.content).toBe('decision reject for proposal prod2-mem-1')
    expect(n.content).not.toContain(sample.action)
  })
  test('meta keys are alphanumeric or underscore only', () => {
    for (const d of ['approve', 'reject', 'revise'] as const) {
      const n = decisionNotification(sample, d, 'u1')
      for (const k of Object.keys(n.meta)) expect(k).toMatch(/^[A-Za-z0-9_]+$/)
      expect(n.meta.kind).toBe('decision')
      expect(n.meta.thread_id).toBe('555')
    }
  })
})
