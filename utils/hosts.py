"""域名 → IP 映射覆盖（进程内的“临时 hosts 文件”）。

背景：anyrouter.top 域名到期后无法通过正常 DNS 解析，但服务器 IP 仍可访问。
这里把域名强制映射到已知 IP，作用范围限定在本进程，覆盖两条访问路径：

- httpx 路径：monkey-patch ``socket.getaddrinfo``，对命中的域名返回映射 IP。
  可返回多个 IP，httpx / httpcore 在建立连接时会按顺序逐个尝试，从而实现 fallback。
  URL、Host 头、TLS SNI、证书校验仍按原域名进行，因此 HTTPS 不受影响
  （前提是服务器证书本身仍有效）。
- 浏览器路径（Chromium 为独立进程，不走 Python 的 socket）：生成
  ``--host-resolver-rules`` 启动参数。注意 Chromium 每个域名只接受单个映射目标，
  不支持单域名多 IP fallback，因此浏览器侧仅使用列表中的首个 IP。

可通过环境变量 ``CHECKIN_HOST_OVERRIDES`` 覆盖默认映射（JSON 对象）：
    {"anyrouter.top": ["47.246.23.192", "47.246.23.200"]}
也兼容单 IP 字符串：{"anyrouter.top": "47.246.23.192"}
"""

from __future__ import annotations

import json
import os
import socket

# 默认映射：域名 -> IP 列表（按顺序尝试）。可用环境变量 CHECKIN_HOST_OVERRIDES 覆盖。
_DEFAULT_HOST_OVERRIDES: dict[str, list[str]] = {
	'anyrouter.top': ['47.246.23.192', '47.246.23.200'],
}

_ENV_KEY = 'CHECKIN_HOST_OVERRIDES'

# 保存原始 getaddrinfo，使 install_dns_override 可幂等调用（不会层层包裹）。
_original_getaddrinfo = None


def _default_overrides() -> dict[str, list[str]]:
	"""返回内置默认映射的深拷贝，避免调用方意外修改模块级常量。"""
	return {host: list(ips) for host, ips in _DEFAULT_HOST_OVERRIDES.items()}


def load_host_overrides() -> dict[str, list[str]]:
	"""加载 host 映射。

	优先读取环境变量 CHECKIN_HOST_OVERRIDES（JSON 对象）；未设置或解析失败时回退默认值。
	"""
	raw = os.getenv(_ENV_KEY, '').strip()
	if not raw:
		return _default_overrides()

	try:
		data = json.loads(raw)
	except json.JSONDecodeError as e:
		print(f'[WARN] {_ENV_KEY} JSON 解析失败: {e}，改用内置默认 host 映射')
		return _default_overrides()

	if not isinstance(data, dict):
		print(f'[WARN] {_ENV_KEY} 必须是 JSON 对象，改用内置默认 host 映射')
		return _default_overrides()

	overrides: dict[str, list[str]] = {}
	for host, ips in data.items():
		if isinstance(ips, str):
			ip_list = [ips.strip()] if ips.strip() else []
		elif isinstance(ips, list):
			ip_list = [str(ip).strip() for ip in ips if str(ip).strip()]
		else:
			continue
		if ip_list:
			overrides[host] = ip_list

	return overrides or _default_overrides()


def install_dns_override(overrides: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
	"""对映射中的域名 monkey-patch socket.getaddrinfo，使其解析到指定 IP。

	幂等：始终基于保存的原始函数重建 patch，重复调用不会层层包裹。
	返回实际生效的映射，便于打印日志。
	"""
	global _original_getaddrinfo

	if overrides is None:
		overrides = load_host_overrides()
	if not overrides:
		return {}

	if _original_getaddrinfo is None:
		_original_getaddrinfo = socket.getaddrinfo
	original = _original_getaddrinfo

	def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
		mapped_ips = overrides.get(host)
		if mapped_ips:
			results: list = []
			for ip in mapped_ips:
				# 对 IP 字面量调用原始 getaddrinfo 不会触发真正的 DNS 查询，
				# 仅用于生成正确的 (family, type, proto, sockaddr) 元组并填入端口。
				try:
					results.extend(original(ip, port, family, type, proto, flags))
				except socket.gaierror:
					continue
			if results:
				return results
		return original(host, port, family, type, proto, flags)

	socket.getaddrinfo = patched_getaddrinfo
	return overrides


def get_chromium_host_resolver_args(overrides: dict[str, list[str]] | None = None) -> list[str]:
	"""生成 Chromium ``--host-resolver-rules`` 启动参数。

	每个域名取列表首个 IP（Chromium 不支持单域名多 IP fallback）。无映射时返回空列表。
	"""
	if overrides is None:
		overrides = load_host_overrides()

	rules = [f'MAP {host} {ips[0]}' for host, ips in overrides.items() if ips]
	if not rules:
		return []
	return [f'--host-resolver-rules={",".join(rules)}']
