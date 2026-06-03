# Hermes Agent 部署改动清单

> 所有改动基于 hermes-agent 主分支。部署时需要逐个 apply。

## 1. 依赖安装

```bash
cd ~/.hermes/hermes-agent
source .venv/bin/activate
pip install redis
```

`clarify` 工具的 ACP 回调需要 `redis` 包来桥接 agent ↔ runner 通信。

---

## 2. toolsets.py — hermes-acp 工具集加入 clarify

**文件**: `toolsets.py`  
**改动**: 在 `hermes-acp` 工具集的 tools 列表中加入 `"clarify"`

```diff
     "hermes-acp": {
-        "description": "Editor integration (VS Code, Zed, JetBrains) — coding-focused tools without messaging, audio, or clarify UI",
+        "description": "Editor integration (VS Code, Zed, JetBrains) and web app backend — includes clarify for interactive confirmation",
         "tools": [
             ...
             "execute_code", "delegate_task",
+            "clarify",
         ],
```

**原因**: ACP 模式下 agent 默认不包含 clarify 工具，导致模型无法调用确认弹窗。

---

## 3. acp_adapter/session.py — clarify_callback 桥接 Redis

**文件**: `acp_adapter/session.py`  
**位置**: `SessionManager._create_agent()` 方法末尾，`return agent` 之前  
**改动**: 添加 `_acp_clarify_callback` 函数并绑定到 `agent.clarify_callback`

```python
        # ── Clarify callback: bridge agent's clarify tool → Redis ──
        # When the agent calls clarify(), this callback writes the request to
        # Redis so the runner can pick it up and show a confirmation modal.
        # It then blocks (sync, on the agent thread) until the user responds.
        def _acp_clarify_callback(question: str, choices=None) -> str:
            import redis as _sync_redis
            import uuid as _uuid

            clarify_id = _uuid.uuid4().hex[:12]
            pending_key = f"hermes:clarify_pending:{session_id}"
            response_key = f"hermes:clarify_response:{session_id}:{clarify_id}"
            notify_channel = f"hermes:clarify_notify:{session_id}"

            # Write pending request to Redis (runner reads this)
            data = {
                "clarify_id": clarify_id,
                "question": question,
                "options": list(choices) if choices else [],
            }
            try:
                r = _sync_redis.Redis.from_url(
                    os.environ.get("REDIS_URL", "redis://localhost:6379")
                )
                r.set(pending_key, json.dumps(data), ex=600)
                r.publish(notify_channel, clarify_id)
            except Exception:
                logger.warning("Failed to write clarify request to Redis", exc_info=True)
                return json.dumps({"error": "Redis unavailable"})

            # Wait for user response (blocks agent thread, up to 5 min)
            pubsub = r.pubsub()
            pubsub.subscribe(notify_channel)
            deadline = time.time() + 300
            try:
                while time.time() < deadline:
                    msg = pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if msg and msg["type"] == "message":
                        resp_val = r.get(response_key)
                        if resp_val:
                            r.delete(response_key)
                            return resp_val.decode("utf-8") if isinstance(resp_val, bytes) else str(resp_val)
                return json.dumps({"choice": "超时"})
            finally:
                pubsub.unsubscribe()
                pubsub.close()

        agent.clarify_callback = _acp_clarify_callback
```

**Redis Key 约定**:
| Key | 用途 |
|-----|------|
| `hermes:clarify_pending:{session_id}` | agent → runner: 待处理的确认请求 (JSON, TTL 600s) |
| `hermes:clarify_response:{session_id}:{clarify_id}` | runner → agent: 用户响应 (纯文本, TTL 60s) |
| `hermes:clarify_notify:{session_id}` | PubSub 通道: 双向通知 |

**流程**:
1. Agent 调用 clarify 工具 → callback 写 `clarify_pending` 到 Redis
2. Callback 订阅 `clarify_notify` 通道并阻塞等待
3. Runner 检测到 tool_call 含 "clarify" → 读 `clarify_pending` → 发 SSE 给前端
4. 用户在前端选择 → API 写 `clarify_response` + publish `clarify_notify`
5. Callback 收到通知 → 读 `clarify_response` → 返回给 agent → agent 继续

---

## 4. (可选) gateway/run.py + tools/approval.py — 审批提示中文化

这两个文件是审批系统的 i18n 改动，与确认弹窗无关，但如果你也需要中文环境：

- `gateway/run.py` L17330: 危险命令审批提示英→中
- `tools/approval.py` L1474: execute_code 描述英→中

---

## 部署检查清单

```bash
# 1. 安装依赖
cd ~/.hermes/hermes-agent && source .venv/bin/activate && pip install redis

# 2. Apply 代码改动 (3个文件必须, 2个可选)
# toolsets.py — hermes-acp 加 clarify
# acp_adapter/session.py — clarify_callback
# gateway/run.py — 审批中文化 (可选)
# tools/approval.py — 审批中文化 (可选)

# 3. 验证
python -c "import redis; print('redis OK')"
grep -n "clarify" toolsets.py  # 应看到 clarify 在 hermes-acp 列表中
grep -n "clarify_callback" acp_adapter/session.py  # 应看到绑定代码

# 4. 重启 runner
# runner 侧代码在 hermes-python 项目中，不在 hermes-agent 中
```
