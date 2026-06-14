# cf-trigger

用 Cloudflare Worker 的 Cron Trigger 定时触发 GitHub Actions 签到，
替换 fork 仓库不可靠的 GitHub `schedule` 触发。

## 原理

```
Cloudflare Cron Trigger（准时） → Worker.scheduled() → POST workflow_dispatch → GitHub Actions 跑 checkin.yml
```

Cloudflare 负责「定时」，GitHub 负责「跑反检测浏览器」，各司其职。

## 部署

```bash
# 1. 生成 GitHub Fine-grained PAT
#    Repository access: 只选 nozhou/anyrouter-check-in
#    Permissions → Actions: Read and write（最小权限，仅够触发 workflow）

# 2. 安装并登录
npm install -g wrangler
wrangler login

# 3. 写入密钥（不会进代码/git）
wrangler secret put GITHUB_TOKEN   # 粘贴上面的 PAT
wrangler secret put TRIGGER_KEY    # 随便设个口令，仅手动测试用

# 4. 部署
wrangler deploy
```

## 验证

```bash
# 手动触发一次（不用等到点），随后去 GitHub Actions 看是否出现新的 workflow_dispatch 运行
curl "https://anyrouter-checkin-trigger.<你的子域>.workers.dev/?key=<你的TRIGGER_KEY>"

# 本地干跑 cron 逻辑
wrangler dev --test-scheduled
curl "http://localhost:8787/__scheduled?cron=17+*/8+*+*+*"
```

成本：Cloudflare 免费计划即含 Cron Triggers，这点调用量完全在免费额度内。
