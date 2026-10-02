// Stan 2026-10-02 決定任何地方都不用 haiku。這個 mod 在 subagent 啟動前檢查模型。
// 擋得到：Agent 工具明確帶 model: "haiku"（或任何含 haiku 的完整 id）。
// 擋不到：沒帶 model、由 agent 定義 frontmatter pin 到 haiku 的；那時模型還沒解析，只能事後記一行。
const HAIKU = /haiku/i

export function register(on) {
  on('agent.spawn', async ($, e, next) => {
    // fork 一律繼承父模型、忽略 model 參數，不用擋
    if (!e.fork && HAIKU.test(e.model ?? '')) {
      return {
        deny: 'Stan 不用 haiku。拿掉 model 參數讓角色 agent 用定義裡的模型，或改帶 model: "sonnet" 或 "opus"，再重派一次。',
      }
    }
    const started = await next(e)
    if (HAIKU.test(started.model ?? '')) {
      $.ui.log(`${e.subagentType} 實際跑在 ${started.model}，它的 agent 定義 pin 了 haiku，要改 frontmatter`)
    }
    return started
  })
}
