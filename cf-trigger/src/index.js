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
	if (res.status !== 204) {
		throw new Error(`dispatch failed: ${res.status} ${await res.text()}`);
	}
}

export default {
	// Cron Trigger 到点调用
	async scheduled(event, env, ctx) {
		ctx.waitUntil(dispatch(env));
	},

	// 可选：方便手动 curl 测试，用 ?key= 做最简单的保护
	async fetch(req, env) {
		const url = new URL(req.url);
		if (!env.TRIGGER_KEY || url.searchParams.get('key') !== env.TRIGGER_KEY) {
			return new Response('forbidden', { status: 403 });
		}
		await dispatch(env);
		return new Response('dispatched\n');
	},
};
