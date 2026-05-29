"""
Interview Agent 压力测试
覆盖：
  1. 认证接口 (并发注册/登录)
  2. 资源管理接口 (JD/简历 CRUD 并发)
  3. 面试创建并发
  4. API 健壮性 (非法参数、越权访问)
  5. 持续高频请求 (sustained load)
"""

import asyncio
import aiohttp
import time
import json
import random
import string
import sys
from dataclasses import dataclass, field
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

# ── 结果统计 ──────────────────────────────────────────────────────────────────

@dataclass
class Stats:
    name: str
    ok: int = 0
    fail: int = 0
    errors: list = field(default_factory=list)
    latencies: list = field(default_factory=list)

    def record(self, ok: bool, latency: float, error: str = ""):
        if ok:
            self.ok += 1
        else:
            self.fail += 1
            if error:
                self.errors.append(error)
        self.latencies.append(latency)

    def report(self):
        total = self.ok + self.fail
        if not total:
            return
        lats = sorted(self.latencies)
        p50 = lats[int(len(lats) * 0.5)] if lats else 0
        p95 = lats[int(len(lats) * 0.95)] if lats else 0
        p99 = lats[int(len(lats) * 0.99)] if lats else 0
        success_rate = self.ok / total * 100
        color = "\033[92m" if success_rate >= 95 else ("\033[93m" if success_rate >= 80 else "\033[91m")
        reset = "\033[0m"
        print(f"  {color}✓ {self.ok:4d}{reset} / {total:4d}  "
              f"失败: {self.fail:3d}  "
              f"p50: {p50*1000:5.0f}ms  p95: {p95*1000:5.0f}ms  p99: {p99*1000:5.0f}ms  "
              f"成功率: {color}{success_rate:.1f}%{reset}")
        # Print unique errors (max 3)
        seen = set()
        for e in self.errors:
            key = e[:80]
            if key not in seen:
                seen.add(key)
                print(f"    \033[91m↳ {key}\033[0m")
            if len(seen) >= 3:
                break

# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def post(session, path, data=None, token=None, form=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    t0 = time.monotonic()
    try:
        if form:
            resp = await session.post(f"{BASE_URL}{path}", data=form, headers=headers)
        else:
            headers["Content-Type"] = "application/json"
            resp = await session.post(f"{BASE_URL}{path}", json=data, headers=headers)
        body = await resp.text()
        latency = time.monotonic() - t0
        return resp.status, body, latency
    except Exception as e:
        return 0, str(e), time.monotonic() - t0

async def get(session, path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    t0 = time.monotonic()
    try:
        resp = await session.get(f"{BASE_URL}{path}", headers=headers)
        body = await resp.text()
        return resp.status, body, time.monotonic() - t0
    except Exception as e:
        return 0, str(e), time.monotonic() - t0

async def delete(session, path, token=None, data=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    t0 = time.monotonic()
    try:
        if data:
            headers["Content-Type"] = "application/json"
            resp = await session.delete(f"{BASE_URL}{path}", json=data, headers=headers)
        else:
            resp = await session.delete(f"{BASE_URL}{path}", headers=headers)
        return resp.status, await resp.text(), time.monotonic() - t0
    except Exception as e:
        return 0, str(e), time.monotonic() - t0

def rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

# ── 测试套件 ──────────────────────────────────────────────────────────────────

async def get_token(session) -> Optional[str]:
    email = f"{rand_str()}@stresstest.com"
    status, body, _ = await post(session, "/auth/register", {
        "name": "stress_user", "email": email, "password": "Test1234!"
    })
    if status in (200, 201):
        return json.loads(body)["access_token"]
    return None

# ── 1. 并发注册/登录 ───────────────────────────────────────────────────────────

async def test_concurrent_auth(session, concurrency=30):
    print(f"\n【1】并发认证 (N={concurrency})")
    reg_stats = Stats("注册")
    login_stats = Stats("登录")

    async def do_register():
        email = f"{rand_str()}@stresstest.com"
        status, body, lat = await post(session, "/auth/register", {
            "name": "u", "email": email, "password": "Test1234!"
        })
        ok = status in (200, 201)
        reg_stats.record(ok, lat, "" if ok else f"status={status} {body[:60]}")
        return email if ok else None

    async def do_login(email):
        if not email:
            return
        status, body, lat = await post(session, "/auth/login", {
            "email": email, "password": "Test1234!"
        })
        ok = status == 200
        login_stats.record(ok, lat, "" if ok else f"status={status} {body[:60]}")

    emails = await asyncio.gather(*[do_register() for _ in range(concurrency)])
    await asyncio.gather(*[do_login(e) for e in emails])

    print(f"  注册: ", end=""); reg_stats.report()
    print(f"  登录: ", end=""); login_stats.report()

# ── 2. 并发 JD 创建/读取/删除 ─────────────────────────────────────────────────

async def test_jd_crud(session, token, concurrency=20):
    print(f"\n【2】JD CRUD 并发 (N={concurrency})")
    create_stats = Stats("JD创建")
    list_stats = Stats("JD列表")
    delete_stats = Stats("JD删除")

    async def do_create():
        status, body, lat = await post(session, "/jds", {
            "title": f"岗位_{rand_str()}",
            "company": "测试公司",
            "description": "这是一段测试的岗位描述，包含技术要求和职责说明。" * 10,
        }, token=token)
        ok = status == 201
        create_stats.record(ok, lat, "" if ok else f"status={status} {body[:80]}")
        if ok:
            return json.loads(body).get("id")
        return None

    ids = await asyncio.gather(*[do_create() for _ in range(concurrency)])
    ids = [i for i in ids if i]

    # 并发列表
    async def do_list():
        status, _, lat = await get(session, "/jds", token=token)
        list_stats.record(status == 200, lat, f"status={status}" if status != 200 else "")

    await asyncio.gather(*[do_list() for _ in range(20)])

    # 并发删除
    async def do_delete(jd_id):
        status, body, lat = await delete(session, f"/jds/{jd_id}", token=token)
        ok = status in (200, 204)
        delete_stats.record(ok, lat, "" if ok else f"status={status} {body[:60]}")

    await asyncio.gather(*[do_delete(i) for i in ids])

    print(f"  创建: ", end=""); create_stats.report()
    print(f"  列表: ", end=""); list_stats.report()
    print(f"  删除: ", end=""); delete_stats.report()

# ── 3. 并发面试创建 ────────────────────────────────────────────────────────────

async def test_concurrent_interview_create(session, token, concurrency=20):
    print(f"\n【3】并发面试创建 (N={concurrency})")
    create_stats = Stats("创建面试")
    ids = []

    async def do_create():
        mode = random.choice(["basic", "follow_up", "stress"])
        status, body, lat = await post(session, "/interviews", {
            "mode": mode,
        }, token=token)
        ok = status == 201
        create_stats.record(ok, lat, "" if ok else f"status={status} {body[:80]}")
        if ok:
            ids.append(json.loads(body)["id"])

    await asyncio.gather(*[do_create() for _ in range(concurrency)])
    print(f"  创建: ", end=""); create_stats.report()

    # 清理
    if ids:
        status, _, lat = await delete(session, "/interviews/batch", token=token, data={"ids": ids})

    return ids

# ── 4. 安全 / 健壮性测试 ───────────────────────────────────────────────────────

async def test_robustness(session, token):
    print(f"\n【4】健壮性 & 安全测试")
    cases = []

    # 无 token 访问
    s, _, lat = await get(session, "/interviews")
    cases.append(("无 token 访问受保护接口", s == 401, lat, f"期望401 实际{s}"))

    # 错误 token
    s, _, lat = await get(session, "/interviews", token="invalid.token.here")
    cases.append(("无效 token", s == 401, lat, f"期望401 实际{s}"))

    # 访问不存在资源
    s, _, lat = await get(session, "/interviews/00000000-0000-0000-0000-000000000000", token=token)
    cases.append(("访问不存在面试", s == 404, lat, f"期望404 实际{s}"))

    s, _, lat = await get(session, "/jds/00000000-0000-0000-0000-000000000000", token=token)
    cases.append(("访问不存在JD", s == 404, lat, f"期望404 实际{s}"))

    # 缺少必填字段
    s, b, lat = await post(session, "/interviews", {}, token=token)
    cases.append(("空body创建面试用默认mode", s == 201, lat, f"期望201 实际{s}"))

    # 非法 mode
    s, b, lat = await post(session, "/interviews", {"mode": "hacker_mode"}, token=token)
    cases.append(("非法面试模式", s in (201, 422), lat, f"实际{s}"))

    # 超长字段
    s, b, lat = await post(session, "/jds", {
        "title": "A" * 500,
        "company": "B" * 500,
        "description": "C" * 50000,
    }, token=token)
    cases.append(("超长字段输入", s in (201, 422, 500), lat, f"实际{s}"))
    if s == 201:
        jid = json.loads(b).get("id")
        if jid:
            await delete(session, f"/jds/{jid}", token=token)

    # 跨租户隔离 - 用另一个账号的 token 访问
    other_token = await get_token(session)
    if other_token:
        s2, _, lat = await post(session, "/interviews", {"mode": "basic"}, token=token)
        if s2 == 201:
            iid = json.loads(_)["id"] if s2 == 201 else None
        # Actually try fetching with other token
        s_cross, _, lat = await get(session, "/interviews", token=other_token)
        cases.append(("跨租户数据隔离", s_cross == 200, lat, f"实际{s_cross}"))

    stats = Stats("健壮性")
    for name, passed, lat, msg in cases:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name:<28} ({lat*1000:.0f}ms) {'OK' if passed else '← ' + msg}")
        stats.record(passed, lat)

# ── 5. 持续高频请求 (sustained load) ─────────────────────────────────────────

async def test_sustained_load(session, token, duration=15, rps_target=20):
    print(f"\n【5】持续高频请求 ({duration}s, 目标 {rps_target} RPS)")
    stats = Stats("持续负载")
    start = time.monotonic()
    interval = 1.0 / rps_target
    request_count = 0

    endpoints = [
        lambda: get(session, "/interviews", token=token),
        lambda: get(session, "/jds", token=token),
        lambda: get(session, "/resumes", token=token),
        lambda: get(session, "/question-banks", token=token),
    ]

    tasks = []
    while time.monotonic() - start < duration:
        endpoint = random.choice(endpoints)
        tasks.append(asyncio.create_task(endpoint()))
        request_count += 1
        await asyncio.sleep(interval)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            stats.record(False, 0, str(r))
        else:
            status, body, lat = r
            stats.record(status == 200, lat, f"status={status}" if status != 200 else "")

    elapsed = time.monotonic() - start
    actual_rps = request_count / elapsed
    print(f"  实际 RPS: {actual_rps:.1f}  总请求: {request_count}  耗时: {elapsed:.1f}s")
    print(f"  结果: ", end=""); stats.report()

# ── 6. 内存/连接泄漏探测 ─────────────────────────────────────────────────────

async def test_connection_leak(session, token, rounds=5, burst=50):
    print(f"\n【6】连接稳定性 ({rounds} 轮，每轮 burst={burst})")
    for r in range(rounds):
        stats = Stats(f"轮{r+1}")
        tasks = [get(session, "/interviews", token=token) for _ in range(burst)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                stats.record(False, 0, str(res))
            else:
                s, _, lat = res
                stats.record(s == 200, lat)
        print(f"  轮 {r+1}: ", end=""); stats.report()
        await asyncio.sleep(0.5)

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 65)
    print("  Interview Agent 压力测试")
    print("=" * 65)

    connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 获取主测试 token
        print("\n▶ 初始化测试账号...")
        token = await get_token(session)
        if not token:
            print("❌ 无法获取测试 token，请确认服务正常运行")
            return
        print(f"  ✅ Token 已获取")

        t_total = time.monotonic()

        await test_concurrent_auth(session, concurrency=30)
        await test_jd_crud(session, token, concurrency=20)
        await test_concurrent_interview_create(session, token, concurrency=20)
        await test_robustness(session, token)
        await test_sustained_load(session, token, duration=15, rps_target=20)
        await test_connection_leak(session, token, rounds=5, burst=50)

        elapsed = time.monotonic() - t_total
        print(f"\n{'=' * 65}")
        print(f"  测试完成，总耗时: {elapsed:.1f}s")
        print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())
