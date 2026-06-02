# Hermes E2E Tests

Hermes 信使应用端到端测试套件，基于 Playwright + pytest。

## 覆盖模块 (88条用例)

| 模块 | 用例数 | 说明 |
|------|--------|------|
| AUTH | 5 | 认证流程：登录/退出/刷新/权限 |
| CONV | 12 | 会话：新建/重命名/置顶/删除/搜索/折叠 |
| CFIRM | 5 | AI确认对话框 |
| FILE | 8 | 文件上传/预览/编辑/版本/工作区 |
| RT | 6 | 圆桌多Agent |
| LDAP | 9 | LDAP身份提供商配置 |
| MAP | 6 | LDAP部门→团队映射 |
| PROF | 7 | 助手管理 |
| ADMIN | 8 | 用户管理 |
| AUDIT | 3 | 审计日志 |
| SYS | 3 | 系统设置 |
| WECOM | 7 | 企业微信SSO |
| THEME | 4 | 主题切换 |
| PROFILE | 3 | 个人资料 |
| TEAM | 5 | 团队功能 |

## 运行

```bash
# 前置条件：服务已启动
make up && make migrate && make seed

# 安装依赖
pip install pytest-playwright
playwright install chromium

# 运行全部测试
cd e2e && pytest

# 运行单个模块
pytest tests/test_auth.py -v
```

## 测试账号

| 账号 | 角色 | 用途 |
|------|------|------|
| admin@hermes.io | super_admin | 全量管理 |
| member@test.com | member | 权限校验 |
| viewer@test.com | viewer | 只读校验 |

## 发现的Bug

- 🐛 member可创建团队 (teams.py 无权限拦截)
- 🐛 空source_value不拒绝 (LDAP映射缺校验)

详见 `e2e-test-report.md` 和 `整改报告.md`。
