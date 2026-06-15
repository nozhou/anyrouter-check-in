// Cloudflare Worker：定时用 workflow_dispatch 触发 GitHub Actions 签到。
// 替换 fork 仓库不可靠的 GitHub schedule 触发。

const OWNER = 'nozhou';
const REPO = 'anyrouter-check-in';
const WORKFLOW = 'checkin.yml'; // 用文件名即可，无需 numeric id

async function dispatch(env) {
	const res = await fetch(
		`https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
		{
			method: 'POST',
			headers: {
				Authorization: `Bearer ${env.GITHUB_TOKEN}`,
				Accept: 'application/vnd.github+json',
				'X-GitHub-Api-Version': '2022-11-28',
				// GitHub API 强制要求 User-Agent，缺了会直接 403
				'User-Agent': 'anyrouter-checkin-trigger',
			},
			// 触发默认分支 main 上的 workflow；如需调试可加 inputs: { debug: 'true' }
			body: JSON.stringify({ ref: 'main' }),
		}
	);

	// workflow_dispatch 成功返回 204 No Content（不是 200，也没有 body）
	if (res.status === 204) {
		console.log('[checkin-trigger] ✅ 已触发 checkin.yml（HTTP 204）');
	} else {
		const body = await res.text();
		console.error(`[checkin-trigger] ❌ 触发失败 HTTP ${res.status}: ${body}`);
		throw new Error(`dispatch failed: ${res.status}`);
	}
}

export default {
	// 纯定时触发器：Cron Trigger 到点调用，无 HTTP 入口
	async scheduled(event, env, ctx) {
		// event.scheduledTime 是本次计划触发的毫秒时间戳，可对比看是否准时
		console.log(
			`[checkin-trigger] ⏰ Cron 触发 cron="${event.cron}" scheduledTime=${new Date(event.scheduledTime).toISOString()}`
		);
		ctx.waitUntil(dispatch(env));
	},
};
