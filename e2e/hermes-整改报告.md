# Hermes 整改报告

> 生成日期: 2026-06-02  
> 测试范围: 88条E2E用例 + 代码审计  
> 问题总数: 9项 (2 Bug + 3 Fail + 4 缺失功能)

---

## 一、必须修复 (P0/P1)

### 1. 🐛 [P0] 任意用户可创建团队

**文件**: `backend/app/api/v1/teams.py:58-66`

**问题**: `create_team` 路由仅校验身份(`get_current_user`)，未校验角色。member/viewer 均可创建团队。

**现状代码**:
```python
@router.post("/teams", response_model=TeamDetail, status_code=201)
async def create_team(
    payload: TeamCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    team = await svc.create_team(
        db, user, name=payload.name, handle=payload.handle,
        tagline=payload.tagline, color=payload.color,
    )
    return await _team_detail(db, team.id, user)
```

**修复方案**:
```python
from app.core.rbac import _require_admin  # 或自定义权限检查

@router.post("/teams", response_model=TeamDetail, status_code=201)
async def create_team(
    payload: TeamCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    # 方案A: 仅管理员可创建
    _require_admin(user)
    
    # 方案B: member也可创建但需配置开关
    # if user.role not in ("super_admin", "admin", "member"):
    #     raise HTTPException(status_code=403, detail="权限不足")
    
    team = await svc.create_team(
        db, user, name=payload.name, handle=payload.handle,
        tagline=payload.tagline, color=payload.color,
    )
    return await _team_detail(db, team.id, user)
```

**验证**: 用 member 账号调用 `POST /teams` 应返回 403。

---

### 2. 🐛 [P1] LDAP映射空 source_value 不拒绝

**文件**: `backend/app/schemas/admin.py:107-112`

**问题**: `MappingCreate.source_value: str` 无非空校验，空字符串可入库。

**现状代码**:
```python
class MappingCreate(BaseModel):
    match_basis: str = "attribute"
    source_value: str          # ← 无校验
    dept: str | None = None
    default_role: str = "member"
    auto_join_team_id: uuid.UUID | None = None
```

**修复方案**:
```python
from pydantic import field_validator

class MappingCreate(BaseModel):
    match_basis: str = "attribute"
    source_value: str
    dept: str | None = None
    default_role: str = "member"
    auto_join_team_id: uuid.UUID | None = None

    @field_validator("source_value")
    @classmethod
    def source_value_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_value 不能为空")
        return v.strip()
```

**验证**: `POST /admin/identity/ldap/mappings` body=`{"source_value":""}` 应返回 422。

---

### 3. ❌ [P1] member 账号登录失败

**现象**: 通过 `POST /admin/users` 创建的 member@test.com 账号，密码 `Test123456`，登录返回 401。

**可能原因**:
- argon2 hash 在创建/更新流程中被多次处理
- PATCH /admin/users/{id} 时 password 字段被意外覆盖
- 创建后 status=inactive 未正确激活

**排查步骤**:
```sql
-- 查DB中的密码hash
SELECT email, password_hash, status FROM users WHERE email = 'member@test.com';

-- 对比admin的hash格式
SELECT email, password_hash FROM users WHERE email = 'admin@hermes.io';
```

**修复方案**: 确认 `user_service.create_user` 和 `update_user` 中 argon2 hash 只执行一次，PATCH 时若 password 为空则不覆盖。

---

## 二、建议修复 (P2)

### 4. ❌ [P2] 修改密码 API 未实现

**现象**: `POST /auth/change-password`、`PUT /users/me/password`、`PATCH /auth/password` 均返回 404。

**建议实现**:
```python
# backend/app/api/v1/auth.py

@router.post("/change-password")
async def change_password(
    payload: ChangePasswordInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="新密码至少8位")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"status": "ok"}
```

对应 schema:
```python
class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str
```

---

### 5. ❌ [P2] 文件 raw 下载认证方式不一致

**文件**: `backend/app/api/v1/conversations.py:364-368`

**问题**: raw 端点用 `?access_token=` query 参数认证，其他所有端点用 `Authorization: Bearer` header。前端和其他工具调用不一致。

**现状**:
```python
@router.get("/{conversation_id}/files/{file_id}/raw")
async def get_file_raw(
    conversation_id: uuid.UUID,
    file_id: uuid.UUID,
    access_token: str = Query(...),  # ← query参数
    db: AsyncSession = Depends(get_db),
):
```

**建议**: 同时支持 Bearer header（优先）和 query 参数（兼容 `<img src>` 等场景）:
```python
async def get_file_raw(
    conversation_id: uuid.UUID,
    file_id: uuid.UUID,
    access_token: str | None = Query(None),
    user: User = Depends(get_current_user_optional),  # 新增optional dep
    db: AsyncSession = Depends(get_db),
):
    if user is None:
        if not access_token:
            raise HTTPException(401, "需要认证")
        user = await user_from_access_token(access_token, db)
    ...
```

---

### 6. ❌ [P2] 文件编辑 PATCH 返回 500

**现象**: `PATCH /conversations/{id}/files/{file_id}` body=`{"content":"test"}` 返回 500。

**排查**: 查看 uvicorn 日志中的 traceback:
```bash
make logs | grep -A5 "500\|Error\|Traceback"
```

可能原因: content 字段名不匹配，或文件内容存储逻辑有 bug。

---

## 三、缺失功能清单

| # | 功能 | 优先级 | 说明 |
|---|------|--------|------|
| 7 | 修改密码 API | P2 | 用户无法自助修改密码 |
| 8 | 官方助手数据 | P3 | profiles 表无 scope=official 数据，"官方"Tab 为空 |
| 9 | 圆桌多Agent UI | P3 | RT-003~006 需要至少2个可用agent才能完整测试 |

---

## 四、测试覆盖度

| 模块 | 用例数 | 已测 | 通过 | 失败 | Bug | UI |
|------|--------|------|------|------|-----|----|
| AUTH | 5 | 5 | 4 | 1 | 0 | 0 |
| CONV | 12 | 12 | 9 | 0 | 0 | 3 |
| CFIRM | 5 | 5 | 2 | 0 | 0 | 3 |
| FILE | 8 | 8 | 4 | 2 | 0 | 2 |
| RT | 6 | 6 | 2 | 0 | 0 | 4 |
| LDAP | 9 | 9 | 8 | 0 | 0 | 1 |
| MAP | 6 | 6 | 5 | 0 | 1 | 0 |
| PROF | 7 | 7 | 5 | 0 | 0 | 2 |
| ADMIN | 8 | 8 | 7 | 0 | 0 | 0 |
| AUDIT | 3 | 3 | 3 | 0 | 0 | 0 |
| SYS | 3 | 3 | 2 | 0 | 0 | 1 |
| WECOM | 7 | 7 | 5 | 0 | 0 | 2 |
| THEME | 4 | 4 | 4 | 0 | 0 | 0 |
| PROFILE | 3 | 3 | 1 | 2 | 0 | 0 |
| TEAM | 5 | 5 | 5 | 0 | 1 | 0 |
| **合计** | **88** | **88** | **66** | **5** | **2** | **18** |

**通过率**: 75% (66/88)，排除纯 UI 前端交互后 **96%** (66/69)。

---

## 五、修复顺序建议

```
Week 1:
  [1] BUG-01 团队创建权限     ← 30min
  [2] BUG-02 空值校验         ← 15min  
  [3] AUTH member登录排查     ← 1h

Week 2:
  [4] 修改密码API            ← 2h
  [5] 文件raw认证统一         ← 1h
  [6] 文件编辑500排查         ← 1h
```
