"""Conversation + message persistence and the send→enqueue hot path."""
from __future__ import annotations

import os
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import redis as redis_core
from app.db.models.agent import Profile
from app.db.models.conversation import Conversation, Message
from app.db.models.user import User
from app.db.models.workspace import WorkspaceFile, WorkspaceFileVersion


async def list_conversations(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    q: str | None = None,
    pinned_only: bool = False,
) -> list[Conversation]:
    from app.db.models.conversation import GroupMember

    # Personal conversations (owned) + group conversations (member of)
    group_subq = (
        select(GroupMember.conversation_id)
        .where(GroupMember.user_id == owner_id)
        .scalar_subquery()
    )
    stmt = select(Conversation).where(
        (Conversation.owner_id == owner_id)
        | ((Conversation.type == "group") & Conversation.id.in_(group_subq))
    )
    if pinned_only:
        stmt = stmt.where(Conversation.pinned.is_(True))
    if q:
        escaped = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(func.lower(Conversation.title).like(f"%{escaped}%", escape="\\"))
    stmt = stmt.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def bulk_delete(
    db: AsyncSession, owner_id: uuid.UUID, ids: list[uuid.UUID]
) -> int:
    res = await db.execute(
        select(Conversation).where(
            Conversation.owner_id == owner_id, Conversation.id.in_(ids)
        )
    )
    convos = list(res.scalars().all())
    for c in convos:
        await db.delete(c)
    await db.commit()
    return len(convos)


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, owner_id: uuid.UUID
) -> Conversation | None:
    from app.db.models.conversation import GroupMember

    res = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            (Conversation.owner_id == owner_id)
            | Conversation.is_channel.is_(True)
            | (Conversation.type == "group"),  # group members can access
        )
    )
    return res.scalar_one_or_none()


async def get_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int | None = None,
    before_id: uuid.UUID | None = None,
) -> list[Message]:
    """Fetch messages, optionally paginated.

    When *limit* is given, returns only the most recent *limit* messages.
    *before_id* (cursor) fetches messages older than the given message id.
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
    )
    if before_id:
        # Sub-select to get the cursor timestamp
        cursor_ts = (
            select(Message.created_at)
            .where(Message.id == before_id)
            .scalar_subquery()
        )
        stmt = stmt.where(Message.created_at < cursor_ts)
    stmt = stmt.order_by(Message.created_at.desc(), Message.role.asc())
    if limit:
        stmt = stmt.limit(limit)
    res = await db.execute(stmt)
    return list(reversed(res.scalars().all()))


async def create_conversation(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    title: str | None,
    primary_agent_id: str,
    profile_id: str | None,
    team_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> Conversation:
    convo = Conversation(
        owner_id=owner_id,
        title=title or "新会话",
        primary_agent_id=primary_agent_id,
        profile_id=profile_id,
        team_id=team_id,
        project_id=project_id,
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return convo


async def _resolve_attached_files(
    db: AsyncSession, file_ids: list[str], conversation_id: str | None = None,
) -> list[dict]:
    """Look up workspace files by id, write to agent workspace dir, return metadata + content.

    Returns [{id, name, kind, workspace_path, content, size_bytes, mime_type}].
    """
    if not file_ids:
        return []

    # MIME type mapping
    MIME_MAP = {
        "md": "text/markdown", "txt": "text/plain", "json": "application/json",
        "csv": "text/csv", "html": "text/html", "htm": "text/html",
        "js": "text/javascript", "ts": "text/javascript", "py": "text/x-python",
        "go": "text/x-go", "rs": "text/x-rust", "yaml": "text/yaml",
        "yml": "text/yaml", "toml": "text/toml", "sh": "text/x-shellscript",
        "bash": "text/x-shellscript", "log": "text/plain", "xml": "text/xml",
        "css": "text/css", "diff": "text/x-diff", "patch": "text/x-diff",
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml",
        "bmp": "image/bmp", "pdf": "application/pdf",
    }
    IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"}
    TEXT_EXTS = {"md", "txt", "json", "csv", "html", "htm", "js", "ts", "py", "go", "rs",
                 "yaml", "yml", "toml", "sh", "bash", "log", "xml", "css", "diff", "patch"}

    # Prepare workspace dir for the agent to access files
    ws_dir = None
    if conversation_id:
        ws_dir = os.path.join(settings.workspace_root, conversation_id, "attachments")
        os.makedirs(ws_dir, exist_ok=True)

    result = []
    for raw_id in file_ids:
        try:
            fid = uuid.UUID(str(raw_id))
        except ValueError:
            continue
        f = await db.get(WorkspaceFile, fid)
        if f is not None:
            file_content = f.content or ""
            ext = (f.kind or "").lower()
            mime = MIME_MAP.get(ext, "application/octet-stream")
            is_image = ext in IMAGE_EXTS
            is_text = ext in TEXT_EXTS

            # Write file content to workspace so agent can read it
            if ws_dir and file_content and not is_image:
                fpath = os.path.join(ws_dir, f.name)
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(file_content)

            result.append({
                "id": str(f.id), "name": f.name, "kind": f.kind,
                "workspace_path": f"attachments/{f.name}" if ws_dir and file_content else None,
                "content": file_content,
                "size_bytes": f.size_bytes or len(file_content),
                "mime_type": mime,
                "is_image": is_image,
                "is_text": is_text,
            })
    return result


async def send_user_only(
    db: AsyncSession,
    convo: Conversation,
    text: str,
    attached_file_ids: list[str] | None = None,
    owner_id: uuid.UUID | None = None,
) -> tuple[Message, None]:
    """Save a user message without triggering agent (for channel mention mode)."""
    user_msg = Message(
        conversation_id=convo.id,
        owner_id=owner_id,
        role="user",
        content={"text": text},
        status="complete",
    )
    db.add(user_msg)
    if convo.title == "新会话":
        convo.title = text[:40]
    await db.commit()
    await db.refresh(user_msg)
    return user_msg, None


async def send_message(
    db: AsyncSession,
    convo: Conversation,
    text: str,
    attached_file_ids: list[str] | None = None,
    owner_id: uuid.UUID | None = None,
    system_prompt: str | None = None,
) -> tuple[Message, Message]:
    """Persist the user turn + an empty streaming agent turn, then enqueue ACP work.

    The per-token hot path does NOT touch the DB — the runner streams via Redis
    Pub/Sub and writes the agent message once on completion.
    """
    attached = await _resolve_attached_files(db, attached_file_ids or [], conversation_id=str(convo.id))
    user_content: dict = {"text": text}
    if attached:
        user_content["files"] = attached

    user_msg = Message(
        conversation_id=convo.id,
        owner_id=owner_id,
        role="user",
        content=user_content,
        status="complete",
    )
    agent_msg = Message(
        conversation_id=convo.id,
        role="agent",
        agent_id=convo.primary_agent_id,
        content={"text": ""},
        status="streaming",
    )
    db.add_all([user_msg, agent_msg])

    # Auto-title from the first user message.
    if convo.title == "新会话":
        convo.title = text[:40]

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(agent_msg)

    # Build prompt — use ACP content blocks for structured attachment handling.
    # Images: ImageContentBlock (base64), Text files: Resource Link + inline fallback.
    _file_write_preamble = (
        "【文件写入规范】当你需要为用户创建、生成或导出文件时，"
        "必须使用 write_file 工具将文件写入当前工作目录（cwd）。"
        "文件路径使用相对路径（如 'README.md'、'src/main.py'），不要使用绝对路径。"
        "不要只在回复文本中说\"文件已生成\"或给出文件路径而不实际写入。"
        "文件名请使用有意义的名称（如 会议纪要.md、report.csv），不要使用临时路径。"
    )
    _clarification_preamble = (
        "\n\n【强制规则：必须先确认再行动】\n"
        "当用户的请求有以下任一情况时，你必须先调用 clarify 工具，不要直接回答：\n"
        "- 请求模糊、有多种理解方式\n"
        "- 需要用户选择方向、风格、范围\n"
        "- 涉及重要决策或有风险的操作\n"
        "- 用户输入非常简短（少于10个字）\n\n"
        "调用方式（必须是工具调用，不要输出文本格式）：\n"
        'clarify(question="问题", choices=["选项A", "选项B", "选项C"])\n'
        'clarify(question="你具体想要什么？")  # 无选项时用 open-ended\n\n'
        "禁止在回复文本中输出 [确认] 或类似的标记格式。必须通过工具调用 clarify。\n"
        "违反此规则会导致用户不满。记住：先问再做。"
    )
    _strict_mode = ""
    if len(text.strip()) < 15:
        _strict_mode = (
            "\n\n【严格模式】用户输入非常简短，你无法确定用户意图。"
            "你必须先调用 clarify 工具询问用户想要什么，不要直接猜测并执行。"
            "这是强制要求，不是建议。"
        )

    # Build content blocks for ACP protocol
    prompt_blocks: list[dict] = []

    # Text block: preambles + user message + inline file references
    prompt_text = text
    if attached:
        text_parts = []
        for f in attached:
            if f.get("is_image"):
                # Images go as separate ImageContentBlock, just reference in text
                text_parts.append(f"[图片附件: {f['name']}]")
            else:
                # Text files: include inline as before (fallback for agents that don't support resource_link)
                content = f.get("content", "")
                if content:
                    orig_len = len(content)
                    if orig_len > 200000:
                        content = content[:200000] + f"\n\n... [文件截断，共 {orig_len} 字符]"
                    text_parts.append(f"【附件: {f['name']}】\n```\n{content}\n```")
                else:
                    text_parts.append(f"【附件: {f['name']}】（文件内容为空）")
        if text_parts:
            prompt_text = f"{text}\n\n" + "\n\n".join(text_parts)

    full_text = f"{_file_write_preamble}{_clarification_preamble}{_strict_mode}\n\n{prompt_text}"
    prompt_blocks.append({"type": "text", "text": full_text})

    # Add Resource Link blocks for attached files (agent can read from workspace)
    for f in attached:
        ws_path = f.get("workspace_path")
        if ws_path and not f.get("is_image"):
            cwd = os.path.join(settings.workspace_root, str(convo.id))
            abs_path = os.path.join(cwd, ws_path)
            prompt_blocks.append({
                "type": "resource_link",
                "uri": f"file://{abs_path}",
                "name": f["name"],
                "mimeType": f.get("mime_type", "application/octet-stream"),
                "size": f.get("size_bytes", 0),
            })

    # Add ImageContentBlock for image attachments
    for f in attached:
        if f.get("is_image") and f.get("content"):
            prompt_blocks.append({
                "type": "image",
                "mimeType": f.get("mime_type", "image/png"),
                "data": f["content"],  # already base64 from upload
            })

    await redis_core.clear_cancel(str(convo.id))
    await redis_core.enqueue_prompt(
        {
            "type": "single",
            "conversation_id": str(convo.id),
            "message_id": str(agent_msg.id),
            "agent_id": convo.primary_agent_id,
            "text": full_text,
            "content_blocks": prompt_blocks if len(prompt_blocks) > 1 else None,
            "system_prompt": system_prompt,
        }
    )
    return user_msg, agent_msg


async def send_roundtable(
    db: AsyncSession,
    convo: Conversation,
    text: str,
    agents: list[str],
    attached_file_ids: list[str] | None = None,
    owner_id: uuid.UUID | None = None,
    system_prompt: str | None = None,
    mentions: list[str] | None = None,
) -> tuple[Message, Message]:
    """Multi-agent turn: one roundtable message holding per-agent replies + a
    synthesized merge. The runner streams each reply in parallel, then merges."""
    attached = await _resolve_attached_files(db, attached_file_ids or [], conversation_id=str(convo.id))
    user_content: dict = {"text": text}
    if attached:
        user_content["files"] = attached
    user_msg = Message(
        conversation_id=convo.id, owner_id=owner_id, role="user", content=user_content, mentions=mentions or [], status="complete"
    )
    rt_msg = Message(
        conversation_id=convo.id,
        role="roundtable",
        agent_id=agents[0],
        content={
            "replies": [
                {"agent_id": a, "text": "", "status": "streaming"} for a in agents
            ],
            "merged": {"text": "", "status": "pending"},
        },
        status="streaming",
    )
    db.add_all([user_msg, rt_msg])
    if convo.title == "新会话":
        convo.title = text[:40]
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(rt_msg)

    prompt_text = text
    if attached:
        parts = []
        for f in attached:
            content = f.get("content", "")
            if content:
                if len(content) > 200000:
                    content = content[:200000] + f"\n\n... [文件截断，共 {len(f.get('content', ''))} 字符]"
                parts.append(f"【附件: {f['name']}】\n```\n{content}\n```")
            else:
                parts.append(f"【附件: {f['name']}】（文件内容为空）")
        file_block = "\n\n".join(parts)
        prompt_text = f"{text}\n\n{file_block}"

    # Inject file-write instructions for roundtable agents too
    _file_write_preamble = (
        "【文件写入规范】当你需要为用户创建、生成或导出文件时，"
        "必须使用 write_file 工具将文件写入当前工作目录（cwd）。"
        "文件路径使用相对路径（如 'README.md'、'src/main.py'），不要使用绝对路径。"
        "不要只在回复文本中说\"文件已生成\"或给出文件路径而不实际写入。"
        "文件名请使用有意义的名称（如 会议纪要.md、report.csv），不要使用临时路径。"
    )
    _clarification_preamble = (
        "\n\n【强制规则：必须先确认再行动】\n"
        "当用户的请求有以下任一情况时，你必须先调用 clarify 工具，不要直接回答：\n"
        "- 请求模糊、有多种理解方式\n"
        "- 需要用户选择方向、风格、范围\n"
        "- 涉及重要决策或有风险的操作\n"
        "- 用户输入非常简短（少于10个字）\n\n"
        "调用方式（必须是工具调用，不要输出文本格式）：\n"
        'clarify(question="问题", choices=["选项A", "选项B", "选项C"])\n'
        'clarify(question="你具体想要什么？")  # 无选项时用 open-ended\n\n'
        "禁止在回复文本中输出 [确认] 或类似的标记格式。必须通过工具调用 clarify。\n"
        "违反此规则会导致用户不满。记住：先问再做。"
    )
    # Strict mode for short prompts: force clarify call
    _strict_mode = ""
    if len(text.strip()) < 15:
        _strict_mode = (
            "\n\n【严格模式】用户输入非常简短，你无法确定用户意图。"
            "你必须先调用 clarify 工具询问用户想要什么，不要直接猜测并执行。"
            "这是强制要求，不是建议。"
        )
    prompt_text = f"{_file_write_preamble}{_clarification_preamble}{_strict_mode}\n\n{prompt_text}"

    await redis_core.clear_cancel(str(convo.id))
    await redis_core.enqueue_prompt(
        {
            "type": "roundtable",
            "conversation_id": str(convo.id),
            "message_id": str(rt_msg.id),
            "agents": agents,
            "text": prompt_text,
            "system_prompt": system_prompt,
        }
    )
    return user_msg, rt_msg


async def _build_preferences_prompt(db: AsyncSession, owner_id: uuid.UUID | None) -> str | None:
    """Load user preferences and format as system prompt snippet."""
    if not owner_id:
        return None
    user = await db.get(User, owner_id)
    if not user or not user.preferences:
        return None
    prefs = user.preferences
    lines = []
    for key, value in prefs.items():
        if value:
            lines.append(f"- {key}: {value}")
    if not lines:
        return None
    return "用户个人偏好记忆（请在回答时参考这些偏好）:\n" + "\n".join(lines)


async def dispatch(
    db: AsyncSession,
    convo: Conversation,
    text: str,
    attached_file_ids: list[str] | None = None,
    owner_id: uuid.UUID | None = None,
    skip_agent: bool = False,
    profile_id_override: str | None = None,
) -> tuple[Message, Message | None]:
    """Route to single or roundtable based on the conversation's active agents."""
    agents = list(convo.active_agent_ids or [convo.primary_agent_id])
    if skip_agent:
        return await send_user_only(db, convo, text, attached_file_ids=attached_file_ids, owner_id=owner_id)

    # Load profile system_prompt — request-level override wins over conversation default
    system_prompt: str | None = None
    effective_profile_id = profile_id_override or convo.profile_id
    if effective_profile_id:
        profile = await db.get(Profile, effective_profile_id)
        if profile:
            system_prompt = profile.system_prompt or None

    # Inject user preferences into system_prompt
    prefs_prompt = await _build_preferences_prompt(db, owner_id)
    if prefs_prompt:
        system_prompt = f"{system_prompt}\n\n{prefs_prompt}" if system_prompt else prefs_prompt

    # Anti-clarify: short follow-up messages are intentional in conversation context
    anti_clarify = (
        "重要：用户在对话中的简短回复（如'继续'、'好的'、'是的'、'ok'、单句指令等）"
        "是明确的意图表达，不要调用 clarify 工具追问。直接执行用户的意图即可。"
        "只有当用户的请求真正存在多种互不相同的理解方式时才需要澄清。"
    )
    system_prompt = f"{system_prompt}\n\n{anti_clarify}" if system_prompt else anti_clarify

    if len(agents) > 1:
        return await send_roundtable(
            db, convo, text, agents,
            attached_file_ids=attached_file_ids, owner_id=owner_id,
            system_prompt=system_prompt,
        )
    return await send_message(
        db, convo, text,
        attached_file_ids=attached_file_ids, owner_id=owner_id,
        system_prompt=system_prompt,
    )


async def set_active_agents(
    db: AsyncSession, convo: Conversation, agent_ids: list[str]
) -> Conversation:
    convo.active_agent_ids = agent_ids or ["hermes"]
    convo.primary_agent_id = convo.active_agent_ids[0]
    await db.commit()
    await db.refresh(convo)
    return convo


async def list_files(db: AsyncSession, conversation_id: uuid.UUID) -> list[WorkspaceFile]:
    res = await db.execute(
        select(WorkspaceFile)
        .where(WorkspaceFile.conversation_id == conversation_id)
        .order_by(WorkspaceFile.updated_at.desc())
    )
    return list(res.scalars().all())


async def delete_conversation(db: AsyncSession, convo: Conversation) -> None:
    await db.delete(convo)
    await db.commit()


async def fork_conversation(
    db: AsyncSession,
    source_id: uuid.UUID,
    owner_id: uuid.UUID,
    before_message_id: uuid.UUID,
) -> tuple[Conversation, list[Message]]:
    """Deep-copy a conversation up to and including a given message."""
    source = await get_conversation(db, source_id, owner_id)
    if not source:
        raise ValueError("conversation not found")
    all_msgs = await get_messages(db, source_id)
    cut = next((i for i, m in enumerate(all_msgs) if m.id == before_message_id), len(all_msgs) - 1)
    fork = Conversation(
        owner_id=owner_id,
        title=f"[分支] {source.title}",
        primary_agent_id=source.primary_agent_id,
        profile_id=source.profile_id,
        team_id=source.team_id,
        project_id=source.project_id,
    )
    db.add(fork)
    await db.flush()
    copied_msgs = []
    for m in all_msgs[: cut + 1]:
        nm = Message(
            conversation_id=fork.id,
            owner_id=m.owner_id,
            role=m.role,
            agent_id=m.agent_id,
            content=m.content,
            status=m.status,
        )
        db.add(nm)
        copied_msgs.append(nm)
    await db.commit()
    await db.refresh(fork)
    return fork, copied_msgs


async def update_file_content(
    db: AsyncSession, f: WorkspaceFile, content: str, author: str | None = None
) -> WorkspaceFile:
    # Save current version before overwriting.
    # For MinIO storage, f.content may be None — read from object storage
    old_content = f.content
    if old_content is None and f.storage_key:
        from app.core import object_storage
        import asyncio
        try:
            raw = await asyncio.to_thread(object_storage.get, f.storage_key)
            old_content = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
        except Exception:
            old_content = None
    if old_content:
        ver = WorkspaceFileVersion(
            file_id=f.id,
            version_num=f.current_version,
            content=old_content,
            size_bytes=f.size_bytes,
            author=author,
        )
        db.add(ver)
    # Keep only the latest 10 versions
    old_versions = (
        await db.execute(
            select(WorkspaceFileVersion)
            .where(WorkspaceFileVersion.file_id == f.id)
            .order_by(WorkspaceFileVersion.version_num.desc())
            .offset(9)  # Keep 10 (0-9), delete from 10th onwards
        )
    ).scalars().all()
    for old in old_versions:
        await db.delete(old)
    f.content = content
    f.size_bytes = len(content.encode("utf-8"))
    f.current_version += 1
    await db.commit()
    await db.refresh(f)
    return f


async def list_file_versions(
    db: AsyncSession, file_id: uuid.UUID
) -> list[WorkspaceFileVersion]:
    res = await db.execute(
        select(WorkspaceFileVersion)
        .where(WorkspaceFileVersion.file_id == file_id)
        .order_by(WorkspaceFileVersion.version_num.desc())
    )
    return list(res.scalars().all())


async def restore_file_version(
    db: AsyncSession, f: WorkspaceFile, version_num: int, author: str | None = None
) -> WorkspaceFile:
    res = await db.execute(
        select(WorkspaceFileVersion).where(
            WorkspaceFileVersion.file_id == f.id,
            WorkspaceFileVersion.version_num == version_num,
        )
    )
    ver = res.scalar_one_or_none()
    if ver is None:
        return f
    return await update_file_content(db, f, ver.content or "", author=author)


# ── Group chat service functions ──────────────────────────────────────────


async def create_group(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    title: str,
    member_user_ids: list[uuid.UUID] | None = None,
    member_agent_ids: list[str] | None = None,
    team_id: uuid.UUID | None = None,
) -> Conversation:
    """创建群聊，自动添加成员。有团队时默认包含全部成员+助手。"""
    from app.db.models.conversation import GroupMember
    from app.db.models.team import Team, TeamMember as TM

    # If team_id, auto-populate members + agents from team
    channel_mode = "mention"
    if team_id:
        team = await db.get(Team, team_id)
        if team:
            channel_mode = team.channel_mode or "mention"
            # Auto-add all team human members (when not explicitly provided)
            if not member_user_ids:
                res = await db.execute(
                    select(TM.user_id).where(TM.team_id == team_id)
                )
                member_user_ids = [row[0] for row in res.all()]
            # Auto-add team shared agents (when not explicitly provided)
            if not member_agent_ids:
                agent_ids = list(team.shared_agents or ["hermes"])
                # Also resolve shared_profile_ids → agent_ids
                if team.shared_profile_ids:
                    from app.db.models.agent import Profile as ProfileModel
                    for pid in team.shared_profile_ids:
                        try:
                            p = await db.get(ProfileModel, uuid.UUID(pid))
                            if p and p.default_agent_id and p.default_agent_id not in agent_ids:
                                agent_ids.append(p.default_agent_id)
                        except Exception:
                            pass
                member_agent_ids = agent_ids

    agent_ids = member_agent_ids or ["hermes"]
    convo = Conversation(
        title=title,
        owner_id=owner_id,
        type="group",
        primary_agent_id=agent_ids[0],
        active_agent_ids=agent_ids,
        team_id=team_id,
        channel_mode=channel_mode,
        visibility="private" if not team_id else "team",
    )
    db.add(convo)
    await db.flush()  # get convo.id

    # Add creator as admin
    db.add(GroupMember(
        conversation_id=convo.id,
        user_id=owner_id,
        role="admin",
    ))

    # Add other human members (dedupe against owner)
    added_users = {owner_id}
    for uid in (member_user_ids or []):
        if uid not in added_users:
            added_users.add(uid)
            db.add(GroupMember(
                conversation_id=convo.id,
                user_id=uid,
                role="member",
            ))

    # Add agent members
    for aid in agent_ids:
        db.add(GroupMember(
            conversation_id=convo.id,
            agent_id=aid,
            role="member",
        ))

    await db.commit()
    await db.refresh(convo)
    return convo


async def get_group_members(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> list:
    """获取群聊成员列表。"""
    from app.db.models.conversation import GroupMember
    res = await db.execute(
        select(GroupMember)
        .where(GroupMember.conversation_id == conversation_id)
        .order_by(GroupMember.joined_at)
    )
    return list(res.scalars().all())


async def add_group_member(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    user_id: uuid.UUID | None = None,
    agent_id: str | None = None,
    role: str = "member",
):
    """添加群聊成员。"""
    from app.db.models.conversation import GroupMember

    if not user_id and not agent_id:
        raise ValueError("必须指定 user_id 或 agent_id")

    # Check if already exists
    existing = await db.execute(
        select(GroupMember).where(
            GroupMember.conversation_id == conversation_id,
            GroupMember.user_id == user_id,
            GroupMember.agent_id == agent_id,
        )
    )
    if existing.scalar_one_or_none():
        return  # already a member

    member = GroupMember(
        conversation_id=conversation_id,
        user_id=user_id,
        agent_id=agent_id,
        role=role,
    )
    db.add(member)

    # Update active_agent_ids if it's an agent
    if agent_id:
        convo = await db.get(Conversation, conversation_id)
        if convo and agent_id not in (convo.active_agent_ids or []):
            convo.active_agent_ids = (convo.active_agent_ids or []) + [agent_id]

    await db.commit()


async def remove_group_member(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    user_id: uuid.UUID | None = None,
    agent_id: str | None = None,
):
    """移除群聊成员。"""
    from app.db.models.conversation import GroupMember

    stmt = select(GroupMember).where(
        GroupMember.conversation_id == conversation_id,
    )
    if user_id:
        stmt = stmt.where(GroupMember.user_id == user_id)
    elif agent_id:
        stmt = stmt.where(GroupMember.agent_id == agent_id)
    else:
        return

    res = await db.execute(stmt)
    member = res.scalar_one_or_none()
    if member:
        await db.delete(member)

        # Update active_agent_ids if it's an agent
        if agent_id:
            convo = await db.get(Conversation, conversation_id)
            if convo:
                convo.active_agent_ids = [
                    a for a in (convo.active_agent_ids or []) if a != agent_id
                ]

        await db.commit()


async def list_group_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[Conversation]:
    """列出用户参与的所有群聊。"""
    from app.db.models.conversation import GroupMember

    stmt = (
        select(Conversation)
        .join(GroupMember, GroupMember.conversation_id == Conversation.id)
        .where(
            Conversation.type == "group",
            GroupMember.user_id == user_id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def is_group_member(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """检查用户是否是群聊成员。"""
    from app.db.models.conversation import GroupMember

    res = await db.execute(
        select(GroupMember).where(
            GroupMember.conversation_id == conversation_id,
            GroupMember.user_id == user_id,
        )
    )
    return res.scalar_one_or_none() is not None


async def resolve_mentions(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    mentions: list[str],
) -> list[str]:
    """将 @mention 文本解析为 agent_id 列表。"""
    if not mentions:
        return []

    # @all_agents → all AI agents in the group
    if "__all_agents__" in mentions:
        members = await get_group_members(db, conversation_id)
        return [m.agent_id for m in members if m.agent_id]

    # @all_humans → no AI agents to resolve, just a notification marker
    if "__all_humans__" in mentions:
        return []

    # Get group's agent members
    members = await get_group_members(db, conversation_id)
    group_agents = [m.agent_id for m in members if m.agent_id]

    resolved = []
    for mention in mentions:
        # Direct match
        if mention in group_agents:
            resolved.append(mention)
            continue

        # Match by profile name
        from sqlalchemy import or_
        res = await db.execute(
            select(Profile).where(
                Profile.is_active.is_(True),
                or_(
                    Profile.name == mention,
                    Profile.handle == mention,
                    Profile.default_agent_id == mention,
                ),
            )
        )
        profile = res.scalars().first()
        if profile and profile.default_agent_id in group_agents:
            resolved.append(profile.default_agent_id)
            continue

        # Fuzzy: prefix match on name
        for agent_id in group_agents:
            res2 = await db.execute(
                select(Profile).where(
                    Profile.default_agent_id == agent_id,
                    Profile.is_active.is_(True),
                ).limit(1)
            )
            p = res2.scalars().first()
            if p and (mention in p.name or p.name.startswith(mention)):
                resolved.append(agent_id)
                break

    return list(set(resolved))  # deduplicate


async def dispatch_group(
    db: AsyncSession,
    convo: Conversation,
    text: str,
    mentions: list[str],
    attached_file_ids: list[str] | None = None,
    owner_id: uuid.UUID | None = None,
    skip_agent: bool = False,
    profile_id_override: str | None = None,
) -> tuple[Message, Message | None]:
    """群聊消息路由：按 channel_mode + mentions 决定走人→人 / 人→机 / 圆桌。"""
    resolved = await resolve_mentions(db, convo.id, mentions)

    # @all_humans → always just save the message (notification only, no AI trigger)
    is_human_broadcast = "__all_humans__" in (mentions or [])

    # channel_mode gating
    mode = getattr(convo, "channel_mode", "mention") or "mention"

    if mode == "off" or skip_agent or is_human_broadcast:
        # off模式或前端显式跳过：只存消息，不触发Agent
        user_msg = Message(
            conversation_id=convo.id,
            owner_id=owner_id,
            role="user",
            content={"text": text},
            mentions=mentions,
            status="complete",
        )
        db.add(user_msg)
        if convo.title == "新会话":
            convo.title = text[:40]
        await db.commit()
        await db.refresh(user_msg)
        return user_msg, None

    if mode == "always" and not resolved:
        # always模式：没有@特定人时，所有agent都回复（圆桌）
        members = await get_group_members(db, convo.id)
        all_agents = [m.agent_id for m in members if m.agent_id]
        if all_agents:
            resolved = all_agents

    if not resolved:
        # mention模式 + 没有@任何Agent：只存消息，不触发Agent
        user_msg = Message(
            conversation_id=convo.id,
            owner_id=owner_id,
            role="user",
            content={"text": text},
            mentions=mentions,
            status="complete",
        )
        db.add(user_msg)
        if convo.title == "新会话":
            convo.title = text[:40]
        await db.commit()
        await db.refresh(user_msg)
        return user_msg, None

    if len(resolved) == 1:
        # 人→机模式：单Agent
        user_msg = Message(
            conversation_id=convo.id,
            owner_id=owner_id,
            role="user",
            content={"text": text},
            mentions=mentions,
            status="complete",
        )
        db.add(user_msg)
        if convo.title == "新会话":
            convo.title = text[:40]
        await db.commit()
        await db.refresh(user_msg)

        # Route to single agent
        system_prompt = None
        # Priority: explicit profile_id_override > @mentioned agent's profile > conversation default
        effective_profile_id = profile_id_override or convo.profile_id
        if not profile_id_override and resolved:
            # No explicit override — try to find the @mentioned agent's profile
            res_p = await db.execute(
                select(Profile).where(
                    Profile.default_agent_id == resolved[0],
                    Profile.is_active.is_(True),
                ).limit(1)
            )
            agent_profile = res_p.scalars().first()
            if agent_profile:
                effective_profile_id = str(agent_profile.id)
        if effective_profile_id:
            profile = await db.get(Profile, effective_profile_id)
            if profile:
                system_prompt = profile.system_prompt or None

        # Inject user preferences
        prefs_prompt = await _build_preferences_prompt(db, owner_id)
        if prefs_prompt:
            system_prompt = f"{system_prompt}\n\n{prefs_prompt}" if system_prompt else prefs_prompt

        # Anti-clarify for short follow-ups
        anti_clarify = (
            "重要：用户在对话中的简短回复（如'继续'、'好的'、'是的'、'ok'、单句指令等）"
            "是明确的意图表达，不要调用 clarify 工具追问。直接执行用户的意图即可。"
            "只有当用户的请求真正存在多种互不相同的理解方式时才需要澄清。"
        )
        system_prompt = f"{system_prompt}\n\n{anti_clarify}" if system_prompt else anti_clarify

        _, agent_msg = await send_message(
            db, convo, text,
            attached_file_ids=attached_file_ids,
            owner_id=owner_id,
            system_prompt=system_prompt,
        )
        return user_msg, agent_msg

    # 圆桌模式：多Agent并行
    system_prompt = None
    effective_profile_id = profile_id_override or convo.profile_id
    if effective_profile_id:
        profile = await db.get(Profile, effective_profile_id)
        if profile:
            system_prompt = profile.system_prompt or None

    # Inject user preferences
    prefs_prompt = await _build_preferences_prompt(db, owner_id)
    if prefs_prompt:
        system_prompt = f"{system_prompt}\n\n{prefs_prompt}" if system_prompt else prefs_prompt

    # Anti-clarify for short follow-ups
    anti_clarify = (
        "重要：用户在对话中的简短回复（如'继续'、'好的'、'是的'、'ok'、单句指令等）"
        "是明确的意图表达，不要调用 clarify 工具追问。直接执行用户的意图即可。"
        "只有当用户的请求真正存在多种互不相同的理解方式时才需要澄清。"
    )
    system_prompt = f"{system_prompt}\n\n{anti_clarify}" if system_prompt else anti_clarify

    return await send_roundtable(
        db, convo, text, resolved,
        attached_file_ids=attached_file_ids,
        owner_id=owner_id,
        system_prompt=system_prompt,
        mentions=mentions,
    )
