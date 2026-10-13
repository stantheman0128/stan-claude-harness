// Stan 2026-10-02 決定不用 haiku；2026-10-13 解禁 Haiku 5.5，改成只擋 Haiku 4.5。這個 mod 在 subagent 啟動前檢查模型。
// CC 2.1.293 起 `haiku` 別名指向 Haiku 5.5，所以 model: "haiku" 放行。
// 擋得到：Agent 工具明確帶 Haiku 4.5 的完整 id（claude-haiku-4-5，含 Bedrock/Vertex 的變體）。
// 擋不到：別名解析到 Haiku 4.5（例如 Bedrock 上的 haiku），或沒帶 model、由 agent 定義 pin 到 Haiku 4.5；那時模型還沒解析，只能事後記一行。
const HAIKU_45 = /haiku[-_. ]?4[-_.]5/i

export function register(on) {
  on('agent.spawn', async ($, e, next) => {
    // fork 一律繼承父模型、忽略 model 參數，不用擋
    if (!e.fork && HAIKU_45.test(e.model ?? '')) {
      return {
        deny: 'Stan 不用 Haiku 4.5。改帶 model: "haiku"（指向 Haiku 5.5）、"sonnet" 或 "opus"，或拿掉 model 參數讓角色 agent 用定義裡的模型，再重派一次。',
      }
    }
    const started = await next(e)
    if (HAIKU_45.test(started.model ?? '')) {
      $.ui.log(`${e.subagentType} 實際跑在 ${started.model}（Haiku 4.5），檢查 agent 定義的 model 或 haiku 別名指向哪裡`)
    }
    return started
  })
}
