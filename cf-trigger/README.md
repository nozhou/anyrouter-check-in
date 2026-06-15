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

# 4. 部署
wrangler deploy
```

## 验证

纯定时触发器，无公网入口。本地干跑 cron 逻辑：

```bash
wrangler dev --test-scheduled
curl "http://localhost:8787/__scheduled?cron=30+0+*+*+*"
```

需要临时手动跑一次时，直接去 GitHub 仓库的 Actions 页面点 "Run workflow"（workflow_dispatch）。

成本：Cloudflare 免费计划即含 Cron Triggers，这点调用量完全在免费额度内。
