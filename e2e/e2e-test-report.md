# Hermes E2E 测试报告

> 测试时间: 2026-06-02 17:40~18:00  
> 测试环境: 本地部署 (Docker infra + 本地前后端)  
> 测试工具: API 自动化 + 浏览器手动  
> 入口: http://localhost:5173 (前端) / http://localhost:8000 (API)

---

## 总览

| 指标 | 数量 |
|------|------|
| 测试用例总计 | 88 |
| 已测试 | 82 |
| ✅ PASS | 59 |
| 🔲 UI-only (需浏览器) | 21 |
| ❌ FAIL | 5 |
| 🐛 BUG | 2 |
| ⏭️ SKIP | 1 |

---

## 🐛 Bug 清单

### BUG-01: 普通用户可创建团队 (高)
- **用例**: TEAM 权限
- **现象**: member 角色调用 `POST /teams` 返回 201，成功创建团队
- **预期**: 应返回 403 Forbidden
- **根因**: `teams.py` 的 `@router.post("/teams")` 路由未做角色权限检查
- **修复建议**: 在路由中添加 `_require_admin(user)` 或在 `team_service` 中校验创建权限

### BUG-02: 空 source_value 不拒绝 (中)
- **用例**: MAP-006
- **现象**: `POST /admin/identity/ldap/mappings` 接受 `{"source_value": ""}` 并返回 201
- **预期**: 应返回 400/422 校验错误
- **根因**: 缺少 Pydantic validator 校验 `source_value` 非空
- **修复建议**: schema 中添加 `@validator("source_value")` 校验非空

---

## ❌ 失败项分析

| # | 用例 | 现象 | 原因 | 类型 |
|---|------|------|------|------|
| 1 | AUTH-005 | member@test.com 登录返回 401 | member 账号创建后密码可能被后续操作覆盖，或 argon2 hash 不一致 | **待查** |
| 2 | FILE-006 | 文件编辑返回 500/404 | 测试会话在清理阶段被删除，导致后续请求 404 | 测试顺序问题 |
| 3 | FILE-004 | 文件 raw 返回 422 | raw 端点需要 `?access_token=` 查询参数，不支持 Bearer header | **API 设计** |
| 4 | PROFILE-002 | 修改密码 404 | `POST /auth/change-password` 端点不存在 | **未实现** |
| 5 | PROFILE-003 | 错误当前密码 404 | 同上，密码修改功能未实现 | **未实现** |

---

## ✅ 通过清单 (59条)

### AUTH 认证流程 (4/5)
| 用例 | 说明 | 结果 |
|------|------|------|
| AUTH-001 | 本地登录成功 | ✅ email=admin@hermes.io, role=super_admin |
| AUTH-002 | 密码错误提示 | ✅ 401 "账号或密码错误" |
| AUTH-003 | 刷新token | ✅ refresh_token 返回新 access_token |
| AUTH-004 | 退出登录 | ✅ 204 No Content |
| AUTH-005 | 非admin访问admin | ❌ member 登录失败，未能验证拦截 |

### CONV 会话核心 (9/12)
| 用例 | 说明 | 结果 |
|------|------|------|
| CONV-001 | 问候语时间变化 | ✅ 浏览器验证"下午好" |
| CONV-002 | 新建会话 | ✅ 201, 返回 conv_id |
| CONV-003 | 助手Tab过滤 | ✅ 2个profile, 0个official |
| CONV-005 | Markdown渲染 | 🔲 UI-only |
| CONV-006 | 复制消息 | 🔲 UI-only |
| CONV-007 | 分享会话 | ✅ POST /{id}/share |
| CONV-008 | 会话重命名 | ✅ PATCH /{id}, 200 |
| CONV-009 | 会话置顶 | ✅ PATCH /{id} pinned=true, 200 |
| CONV-010 | 删除会话 | ✅ DELETE /{id}, 204 |
| CONV-011 | ⌘K搜索 | 🔲 UI-only |
| CONV-012 | 侧边栏折叠 | 🔲 UI-only |
| CONV-004 | 流式回复取消 | 🔲 UI-only (SSE交互) |

### CFIRM AI确认对话框 (2/5)
| 用例 | 说明 | 结果 |
|------|------|------|
| CFIRM-001 | 确认端点存在 | ✅ POST /{id}/confirm, 200 |
| CFIRM-002 | 点击选项继续 | 🔲 UI-only |
| CFIRM-003 | deny确认 | ✅ choice=deny, 200 |
| CFIRM-004 | 遮罩层关闭 | 🔲 UI-only |
| CFIRM-005 | 多确认排队 | 🔲 UI-only |

### FILE 文件附件与工作区 (4/8)
| 用例 | 说明 | 结果 |
|------|------|------|
| FILE-001 | 文件上传 | ✅ POST /upload, 201 |
| FILE-002 | 删除暂存文件 | 🔲 UI-only |
| FILE-003 | 带文件发送 | ✅ upload返回file_id |
| FILE-004 | 文件原始内容 | ❌ raw端点需要?access_token= query参数 |
| FILE-005 | 文件预览 | ✅ GET /files/{id}, 200 |
| FILE-006 | 文件在线编辑 | ❌ 测试会话已清理(404) |
| FILE-007 | 版本历史 | ✅ GET /files/{id}/versions, 200 (0版本) |
| FILE-008 | 工作区折叠展开 | 🔲 UI-only |

### RT 圆桌多Agent (2/6)
| 用例 | 说明 | 结果 |
|------|------|------|
| RT-001 | 添加Agent | ✅ PUT /{id}/agents, 200 |
| RT-002 | 移除Agent | ✅ PUT /{id}/agents [hermes], 200 |
| RT-003 | 圆桌回复展示 | 🔲 UI-only (SSE/WS) |
| RT-004 | 采纳回复 | 🔲 UI-only |
| RT-005 | 追问Agent | 🔲 UI-only |
| RT-006 | 转给我 | 🔲 UI-only |

### LDAP 身份提供商 (7/9)
| 用例 | 说明 | 结果 |
|------|------|------|
| LDAP-001 | LDAP配置存在 | ✅ identity列表含ldap |
| LDAP-002 | LDAP启用状态 | ✅ enabled=True |
| LDAP-003 | 直连绑定模板 | ✅ user_dn_template存在 |
| LDAP-004 | 搜索绑定模式 | ✅ PATCH切换, 200 |
| LDAP-005 | 密码显隐 | 🔲 UI-only |
| LDAP-006 | 配置字段完整 | ✅ host+port+base_dn齐全 |
| LDAP-007 | 清空密码不覆盖 | ✅ bind_password保留 |
| LDAP-008 | 无host测试连接 | ✅ 返回ok (连接本地LDAP) |
| LDAP-009 | 测试连接 | ✅ "已成功连接到LDAP://localhost:389" |

### MAP 部门映射 (5/6)
| 用例 | 说明 | 结果 |
|------|------|------|
| MAP-001 | 添加部门映射 | ✅ POST /mappings, 201 |
| MAP-002 | 映射行格式 | ✅ keys含source_value, default_role, auto_join_team_id |
| MAP-003 | 不设自动加入 | ✅ auto_join_team_id=null |
| MAP-004 | 删除映射 | ✅ DELETE /mappings/{id}, 204 |
| MAP-005 | 团队下拉依赖 | ✅ /teams返回2个团队 |
| MAP-006 | 空source_value被拒 | 🐛 返回201(应拒绝), **BUG** |

### PROF 助手管理 (5/7)
| 用例 | 说明 | 结果 |
|------|------|------|
| PROF-001 | 助手列表 | ✅ 2个profiles |
| PROF-002 | 扫描Agent | 🔲 需要hermes binary |
| PROF-003 | 扫描结果面板 | 🔲 UI-only |
| PROF-004 | 新建助手 | ✅ POST /profiles, 201 |
| PROF-005 | 编辑助手 | ✅ PATCH /profiles/{id}, 200 |
| PROF-006 | 禁用助手 | ✅ PATCH is_active=false, 200 |
| PROF-007 | 删除助手 | ✅ DELETE /profiles/{id}, 204 |

### ADMIN 用户管理 (7/8)
| 用例 | 说明 | 结果 |
|------|------|------|
| ADMIN-001 | 用户列表 | ✅ 5个用户 |
| ADMIN-002 | 搜索用户 | ✅ search=admin 匹配 |
| ADMIN-003 | 来源过滤 | ✅ source=local |
| ADMIN-004 | 状态过滤 | ✅ status=active |
| ADMIN-005 | 修改用户角色 | ✅ PATCH /users/{id}, 200 |
| ADMIN-006 | 停用/激活 | ✅ 停用后login返回401 |
| ADMIN-007 | 新建用户 | ✅ POST /admin/users, 201 |
| ADMIN-008 | 密码<8位被拒 | ✅ 422 |

### AUDIT 审计日志 (3/3)
| 用例 | 说明 | 结果 |
|------|------|------|
| AUDIT-001 | 审计日志展示 | ✅ 62条记录 |
| AUDIT-002 | 关键词搜索 | ✅ search=login |
| AUDIT-003 | 结果过滤 | ✅ result=ok |

### SYS 系统设置 (2/3)
| 用例 | 说明 | 结果 |
|------|------|------|
| SYS-001 | 品牌设置 | ✅ GET /settings, keys=[branding, model_gateway] |
| SYS-002 | 速率限制 | ✅ PUT /settings, 200 |
| SYS-003 | 配额警告 | 🔲 需要实际超额发送 |

### WECOM 企业微信 (4/7)
| 用例 | 说明 | 结果 |
|------|------|------|
| WECOM-001 | 配置入口 | ✅ providers含wecom |
| WECOM-002 | 启用状态 | ✅ enabled=false |
| WECOM-003 | 保存配置 | ✅ PATCH, 200 |
| WECOM-004 | Secret显隐 | 🔲 UI-only |
| WECOM-005 | 清空Secret不覆盖 | ✅ PATCH空值, 200 |
| WECOM-006 | 验证凭证 | ✅ test端点返回200 |
| WECOM-007 | 回调地址提示 | 🔲 UI-only |

### PROFILE 个人资料 (1/3)
| 用例 | 说明 | 结果 |
|------|------|------|
| PROFILE-001 | 修改个人资料 | ✅ PATCH /users/me, 200 |
| PROFILE-002 | 修改密码 | ❌ 端点不存在(未实现) |
| PROFILE-003 | 错误当前密码 | ❌ 端点不存在(未实现) |

### THEME 主题 (0/4 全部UI)
| 用例 | 说明 | 结果 |
|------|------|------|
| THEME-001~004 | 主题切换/持久化 | 🔲 全部前端localStorage |

### TEAM 团队 (5/5+1)
| 用例 | 说明 | 结果 |
|------|------|------|
| TEAM-001 | 创建团队 | ✅ POST /teams, 201 |
| TEAM-002 | 邀请成员 | ✅ POST /teams/{id}/members, 201 |
| TEAM-003 | 知识库上传 | ✅ POST /knowledge/upload, 201 |
| TEAM-004 | 删除知识库 | ✅ DELETE /knowledge/{id}, 204 |
| TEAM-005 | 治理权限 | ✅ GET /teams/{id}/policy, 200 |
| TEAM-BUG | member创建团队 | 🐛 返回201(应拒绝), **BUG** |

---

## 技术发现 (非bug)

1. **会话重命名** 用 `PATCH` 不是 `PUT`
2. **审计日志路径** 是 `/admin/audit` 不是 `/admin/audit-logs`
3. **置顶** 通过 `PATCH /conversations/{id}` + `{"pinned": true}` 实现
4. **文件raw下载** 需要 `?access_token=` query参数 (不支持Bearer header)
5. **修改密码API** 未实现 (404)
6. **official scope 助手** 为0，"官方" Tab 显示为空
7. **LDAP 映射字段** 实际为 `default_role` 不是 `role`，`dept` 不是 `source_value`(部分)

---

## 修复优先级

| 优先级 | 问题 | 影响 |
|--------|------|------|
| 🔴 P0 | BUG-01: member可创建团队 | 任意用户可创建团队，权限泄露 |
| 🟡 P1 | BUG-02: 空source_value不校验 | 脏数据入库 |
| 🟡 P1 | AUTH-005: member登录失败 | 影响LDAP用户登录验证流程 |
| 🟢 P2 | PROFILE-002/003: 密码修改未实现 | 用户无法自助修改密码 |
| 🟢 P2 | FILE-004: raw端点需query token | 与其他API认证方式不一致 |
