import { expect, test } from 'claude-code/testing'

const TASK = { prompt: 'Read README.md.', description: 'read readme' }

test('明確帶 Haiku 4.5 的派工被擋下', async ($, on) => {
  on('agent.spawn', () => ({ model: 'claude-haiku-4-5', agentId: 'a1' }))
  const r = await $.agent.spawn({ ...TASK, model: 'claude-haiku-4-5-20251001' })
  expect(r.deny).toMatch(/Haiku 4\.5/)
  expect(r.agentId).toBeUndefined()
})

test('帶 haiku 別名（Haiku 5.5）的派工照常啟動、不記 log', async ($, on) => {
  const logs: string[] = []
  on('agent.spawn', () => ({ model: 'claude-haiku-5-5', agentId: 'a2' }))
  on('ui.log', ($, e) => {
    logs.push(e.text)
    return { value: undefined }
  })
  const r = await $.agent.spawn({ ...TASK, model: 'haiku' })
  expect(r.deny).toBeUndefined()
  expect(r.agentId).toBe('a2')
  expect(logs.length).toBe(0)
})

test('帶 sonnet 的派工照常啟動', async ($, on) => {
  on('agent.spawn', () => ({ model: 'claude-sonnet-5-5', agentId: 'a3' }))
  const r = await $.agent.spawn({ ...TASK, model: 'sonnet' })
  expect(r.deny).toBeUndefined()
  expect(r.agentId).toBe('a3')
})

test('沒帶 model、定義 pin 到 Haiku 4.5：照常啟動並記一行', async ($, on) => {
  const logs: string[] = []
  on('agent.spawn', () => ({ model: 'claude-haiku-4-5', agentId: 'a4' }))
  on('ui.log', ($, e) => {
    logs.push(e.text)
    return { value: undefined }
  })
  const r = await $.agent.spawn({ ...TASK, subagentType: 'some-plugin-agent' })
  expect(r.agentId).toBe('a4')
  expect(logs.length).toBe(1)
  expect(logs[0]).toContain('some-plugin-agent')
})
