export const meta = {
  name: 'cascade',
  description: 'Run each task cheap-first; an independent verifier runs its check; on failure re-dispatch one rung higher with a handoff (Sonnet high, Opus high, Fable high, Fable xhigh), then stop and report',
  whenToUse: 'Bulk, independent tasks that each come with a runnable check (tests, build, a command, a concrete acceptance test). Not for open-ended design work, and not for tasks that edit the same files unless sequential is true.',
  phases: [
    { title: 'sonnet-high', detail: 'mech-executor, Sonnet 5.5 @ high' },
    { title: 'opus-high', detail: 'executor, Opus 5.5 @ high' },
    { title: 'fable-high', detail: 'executor-high prompt on Fable 5.2 @ high', model: 'fable' },
    { title: 'fable-xhigh', detail: 'executor-high prompt on Fable 5.2 @ xhigh', model: 'fable' },
    { title: 'check', detail: 'verifier, Opus 5.5 @ high, read and run only' },
  ],
}

// 用法（2026-11-23，Stan 核可 cascade）：
//   Workflow({ name: 'cascade', args: {
//     context: '共用說明：repo 路徑、慣例、只准碰哪些路徑',
//     tasks: [{ id: 'fix-parser', task: '要做什麼', check: '怎麼驗，例如在 X 跑 npm test 要全過' }],
//     start: 0, top: 3,        // 預設從 Sonnet high 起、最高到 Fable xhigh；單一 task 可帶自己的 start／top
//     sequential: false,       // task 會改到同一批檔案時設 true
//   } })
// 每一格做完都由 verifier 獨立跑 check；沒過才升一格，前一格改過的檔案留在原地，交接寫進下一格的派工單。
// worker 回報 blocked（缺輸入、規格不清）就停在那一格，不升級：換大模型解決不了規格問題。
// 到頂還沒過就停，max 不在梯子上，要不要開由 Stan 決定。
// Opus high 之後直接換 Fable high、不走 Opus xhigh：官方「If you're past high, test the next model up at a lower effort instead.」
// （claude.dev which-claude-model-should-you-build-with，2026-11-09），而且 Fable 5.2 high 在 AA v5.0.1 已高過 Opus max。
// 修既有 bug、資安這類一開始就該 xhigh 的工作，不要丟進這個梯子，直接派 executor-high 或 security-executor。

const LADDER = [
  { name: 'sonnet-high', agentType: 'mech-executor' },
  { name: 'opus-high', agentType: 'executor' },
  { name: 'fable-high', agentType: 'executor-high', model: 'fable', effort: 'high' },
  { name: 'fable-xhigh', agentType: 'executor-high', model: 'fable', effort: 'xhigh' },
]

// 官方原文，platform.claude.com prompting-claude-sonnet-5-5「Steer initiative and scope」節（2026-11-23 讀）
const SONNET_STOP = 'When the work the user asked for is done and its checks pass, stop and report. Don\'t start extra rounds of review or hardening on your own, and don\'t launch reviewer subagents unless the user asked for a review. If you think a deeper review is worth doing, say so at the end.'

// 官方原文，prompting-claude-fable-5-2#finish-the-whole-task（2026-11-23 讀）
const FABLE_FINISH = `# Finishing work
Please avoid stopping while you still owe work the user asked for. Be persistent and do not stop unless needed.

While status notes are welcome, as is clarifying with the user on open decisions, carry on with work that does not depend on the user's answer without unnecessary stops.

If you notice yourself inviting the user to redirect you or offering to wait, instead proceed on the next part of the task. You may meet ordinary obstacles like errors, timeouts, locked files, empty results or failing tools. Diagnose them first, and when they are not real blockers, work through them with the access you have (wait and retry, fix the request, use another tool or source) rather than stopping unnecessarily.

If someone clearly decided something is a hard blocker, such as a file marked not to be touched, access that was intentionally withheld, or a safety guardrail, leave it alone, say plainly what you found, and look for another safe way to finish the task. Stopping before the task is complete is very rarely merited, as in when the task can't move forward without user input, or where the blocker is deliberate and should not be worked past. This does not override the need for confirmation on risky or destructive actions.`

const WORK = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['done', 'partial', 'blocked'], description: 'blocked = cannot proceed without missing input or a decision' },
    changed: { type: 'array', items: { type: 'string' }, description: 'paths you created or modified' },
    check_ran: { type: 'string', description: 'the exact check command(s) you ran, or "not run: <reason>"' },
    check_output_tail: { type: 'string', description: 'last lines of the real check output' },
    notes: { type: 'string', description: 'what you did, what is left, anything the next person must know' },
  },
  required: ['status', 'changed', 'check_ran', 'check_output_tail', 'notes'],
}

const VERDICT = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    evidence: { type: 'string', description: 'commands you ran and the decisive output lines' },
  },
  required: ['pass', 'evidence'],
}

function clip(s, n) {
  s = String(s == null ? '' : s)
  return s.length > n ? s.slice(0, n) + ' …[cut]' : s
}

function workerPrompt(t, rungIndex, handoff, context) {
  const rung = LADDER[rungIndex]
  const parts = []
  if (context) parts.push(`## Shared context\n${context}`)
  parts.push(`## Task ${t.id}\n${t.task}`)
  parts.push(`## How this will be checked\nAfter you finish, an independent verifier will run this check: ${t.check}\nRun the check yourself before you report and paste the tail of its real output. If you could not run it, say which check did not run and why. Do not edit the check or the tests to make them pass unless the task asks for that.`)
  if (handoff.length) {
    parts.push(`## Previous attempts\nEarlier attempts on cheaper rungs did not pass the check. Their edits are still in the working tree: keep what is right, fix or revert what is wrong.\n\n${handoff.join('\n\n')}`)
  }
  parts.push('## Scope\nChange only what this task needs. If the task cannot be done without missing input or a decision from Stan, stop and report status "blocked" with what is missing.')
  if (rung.name === 'sonnet-high') parts.push(SONNET_STOP)
  if (rung.model === 'fable') parts.push(`${FABLE_FINISH}\n\nBack every technical claim in your report with a file:line or tool output. If an input you need is missing, stop and report it instead of handing in placeholder work.`)
  return parts.join('\n\n')
}

function verifierPrompt(t, report, context) {
  return `${context ? `Shared context: ${context}\n\n` : ''}Independently decide whether task ${t.id} is done. Read and run only.

Task: ${t.task}
Check to run: ${t.check}

The worker reported:
${clip(JSON.stringify(report, null, 1), 4000)}

Run the check yourself; do not rely on the worker's output. pass=true only if the check really passes and the task as written is done. If it fails, put the failing command and output lines in evidence.`
}

async function runTask(t, args) {
  const start = Number.isInteger(t.start) ? t.start : (Number.isInteger(args.start) ? args.start : 0)
  const top = Math.min(Number.isInteger(t.top) ? t.top : (Number.isInteger(args.top) ? args.top : LADDER.length - 1), LADDER.length - 1)
  const attempts = []
  const handoff = []
  for (let i = start; i <= top; i++) {
    const rung = LADDER[i]
    const opts = { label: `${t.id}:${rung.name}`, phase: rung.name, schema: WORK, agentType: rung.agentType }
    if (rung.model) opts.model = rung.model
    if (rung.effort) opts.effort = rung.effort
    let report = await agent(workerPrompt(t, i, handoff, args.context), opts)
    if (!report) report = await agent(workerPrompt(t, i, handoff, args.context), { ...opts, label: `${t.id}:${rung.name}:retry` })
    if (!report) {
      attempts.push({ rung: rung.name, status: 'no-report', pass: false, evidence: 'worker returned nothing twice' })
      handoff.push(`Attempt on ${rung.name}: the worker returned nothing.`)
      log(`${t.id}: ${rung.name} returned nothing, escalating`)
      continue
    }
    if (report.status === 'blocked') {
      attempts.push({ rung: rung.name, status: 'blocked', pass: false, evidence: report.notes })
      log(`${t.id}: blocked at ${rung.name}, not escalating (missing input or decision)`)
      return { id: t.id, result: 'blocked', rung: rung.name, attempts }
    }
    const vopts = { label: `${t.id}:check@${rung.name}`, phase: 'check', schema: VERDICT, agentType: 'verifier' }
    let verdict = await agent(verifierPrompt(t, report, args.context), vopts)
    if (!verdict) verdict = await agent(verifierPrompt(t, report, args.context), { ...vopts, label: `${t.id}:check@${rung.name}:retry` })
    if (!verdict) {
      attempts.push({ rung: rung.name, status: report.status, pass: null, evidence: 'verifier returned nothing twice' })
      log(`${t.id}: verifier returned nothing after ${rung.name}, stopping this task unverified`)
      return { id: t.id, result: 'unverified', rung: rung.name, attempts }
    }
    attempts.push({ rung: rung.name, status: report.status, changed: report.changed, pass: verdict.pass, evidence: clip(verdict.evidence, 1500) })
    if (verdict.pass) {
      log(`${t.id}: passed at ${rung.name}`)
      return { id: t.id, result: 'passed', rung: rung.name, attempts }
    }
    handoff.push(`Attempt on ${rung.name} (status ${report.status}). Changed: ${(report.changed || []).join(', ') || 'nothing'}.\nWorker notes: ${clip(report.notes, 1200)}\nVerifier said: ${clip(verdict.evidence, 2000)}`)
    if (i < top) log(`${t.id}: failed the check at ${rung.name}, escalating to ${LADDER[i + 1].name}`)
  }
  log(`${t.id}: still failing at ${LADDER[top].name}; stopped (max is not on the ladder, Stan decides)`)
  return { id: t.id, result: 'failed', rung: LADDER[top].name, attempts }
}

if (!args || !Array.isArray(args.tasks) || !args.tasks.length) {
  throw new Error('cascade needs args.tasks: [{ id, task, check, start?, top? }], optional args.context / start / top / sequential')
}
for (const t of args.tasks) {
  if (!t.id || !t.task || !t.check) throw new Error(`task ${JSON.stringify(t.id)} needs id, task and check`)
}

let results
if (args.sequential) {
  results = []
  for (const t of args.tasks) results.push(await runTask(t, args))
} else {
  results = await pipeline(args.tasks, t => runTask(t, args))
}
results = results.map((r, i) => r || { id: args.tasks[i].id, result: 'error', attempts: [] })

const count = k => results.filter(r => r.result === k).length
return {
  summary: `${count('passed')} passed, ${count('failed')} failed at the top rung, ${count('blocked')} blocked, ${count('unverified')} unverified, ${count('error')} errors`,
  results,
}
