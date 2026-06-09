<script setup lang="ts">
/* Personal settings — uses the prototype's user-page styles (.up-*). 个人资料
   editing is wired to PATCH /users/me; other tabs reproduce the structure. */
import { computed, onMounted, reactive, ref, watch } from "vue";
import Icon from "@/components/Icon.vue";
import { http } from "@/api/client";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { useNotificationStore } from "@/stores/notifications";
import { memoryApi, type Memory } from "@/api/memory";

const auth = useAuthStore();
const ns = useNotificationStore();
const tab = ref<"profile" | "prefs" | "security" | "notify" | "memory">("profile");
const COLORS = ["#b8852a", "#3a6da1", "#8a5aa1", "#5b8a4a", "#c45a3a", "#3a8a7a", "#6a3aa1", "#1d1a14"];

// ── profile form ──
const form = reactive({
  name: auth.user?.name || "",
  handle: auth.user?.handle || "",
  title: auth.user?.title || "",
  department: auth.user?.department || "",
  bio: "",
  color: auth.user?.color || "#b8852a",
});
const initial = JSON.stringify({ ...form });
const dirty = computed(() => JSON.stringify({ ...form }) !== initial);
const saving = ref(false);

watch(
  () => auth.user,
  (u) => {
    if (u) {
      form.name = u.name;
      form.handle = u.handle || "";
      form.title = u.title || "";
      form.department = u.department || "";
      form.color = u.color || "#b8852a";
    }
  },
);

async function save() {
  saving.value = true;
  try {
    await http.patch("/users/me", { ...form });
    auth.user = await authApi.me();
    ns.toast("个人资料已保存");
  } catch {
    ns.toast("保存失败，请重试", "error");
  } finally {
    saving.value = false;
  }
}

// ── security ──
const twoFaEnabled = ref(false);
const sessions = ref([
  { id: "current", device: navigator.userAgent.includes("Mobile") ? "移动设备" : "当前浏览器", ip: "—", ts: new Date().toISOString(), current: true },
]);
async function revokeSession(id: string) {
  sessions.value = sessions.value.filter((s) => s.id !== id);
  try {
    await http.delete(`/users/me/sessions/${id}`);
  } catch { /* endpoint may not exist yet */ }
  ns.toast("会话已撤销");
}
function relTime(ts: string) {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}

// ── personal preferences memory ──
interface PrefItem { key: string; value: string; label: string; placeholder: string }
const PREF_TEMPLATES: Omit<PrefItem, 'value'>[] = [
  { key: '称呼', label: '称呼偏好', placeholder: '例如：叫我庭辉、用"你"称呼我' },
  { key: '语言风格', label: '语言风格', placeholder: '例如：简洁直接、技术范、轻松口语化' },
  { key: '回复格式', label: '回复格式偏好', placeholder: '例如：用表格对比、用要点列表、先结论后解释' },
  { key: '技术栈', label: '常用技术栈', placeholder: '例如：Vue3+FastAPI、Python、SQLAlchemy' },
  { key: '专业领域', label: '专业领域', placeholder: '例如：ERP运维、A股投资、全栈开发' },
  { key: '兴趣爱好', label: '兴趣爱好', placeholder: '例如：AI学习、投资理财、效率工具' },
  { key: '时区作息', label: '时区与作息', placeholder: '例如：UTC+8，工作日9-18点在线' },
  { key: '工作习惯', label: '工作习惯', placeholder: '例如：喜欢先看代码再问问题、偏好详细步骤' },
]
const prefsList = ref<PrefItem[]>([])
const prefsSaving = ref(false)
const prefsDirty = ref(false)

function initPrefs() {
  const saved = auth.user?.preferences || {}
  prefsList.value = PREF_TEMPLATES.map(t => ({
    ...t,
    value: (saved as Record<string, string>)[t.key] || '',
  }))
  // Load any custom keys not in templates
  for (const [k, v] of Object.entries(saved as Record<string, string>)) {
    if (!PREF_TEMPLATES.find(t => t.key === k)) {
      prefsList.value.push({ key: k, value: v, label: k, placeholder: '自定义偏好' })
    }
  }
  prefsDirty.value = false
}

function addCustomPref() {
  prefsList.value.push({ key: '', value: '', label: '自定义', placeholder: '输入偏好名称' })
  prefsDirty.value = true
}

function removePref(index: number) {
  prefsList.value.splice(index, 1)
  prefsDirty.value = true
}

function onPrefChange() {
  prefsDirty.value = true
}

async function savePrefs() {
  prefsSaving.value = true
  try {
    const prefs: Record<string, string> = {}
    for (const p of prefsList.value) {
      const k = p.key.trim()
      const v = p.value.trim()
      if (k && v) prefs[k] = v
    }
    await http.patch('/users/me', { preferences: prefs })
    auth.user = await authApi.me()
    prefsDirty.value = false
    ns.toast('偏好记忆已保存，AI 会在回答时参考你的偏好')
  } catch {
    ns.toast('保存失败', 'error')
  } finally {
    prefsSaving.value = false
  }
}

watch(() => auth.user, () => { initPrefs() }, { immediate: true })

// ── Agent memory ──
const MEMORY_SECTIONS = [
  { key: "notes" as const,        label: "我的笔记",   desc: "写给 AI 的备注、提醒、任务背景",       placeholder: "例如：正在推进的项目、需要 AI 记住的关键信息…" },
  { key: "user_profile" as const, label: "用户画像",   desc: "AI 对你的理解（职业背景、偏好风格等）", placeholder: "例如：全栈工程师，偏好简洁直接的回答，主要使用 Vue3 + FastAPI…" },
  { key: "soul" as const,         label: "个性设定",   desc: "AI 的角色定位与沟通风格",               placeholder: "例如：以一位有条理的技术顾问角色与我对话，避免过度赘述…" },
] as const;

const memoryData = ref<Memory>({ notes: null, user_profile: null, soul: null });
const memoryEditing = ref<Record<string, boolean>>({ notes: false, user_profile: false, soul: false });
const memoryDrafts = ref<Record<string, string>>({ notes: "", user_profile: "", soul: "" });
const memorySaving = ref<Record<string, boolean>>({ notes: false, user_profile: false, soul: false });
const memoryLoading = ref(false);

async function loadMemory() {
  memoryLoading.value = true;
  try {
    memoryData.value = await memoryApi.get();
  } catch { /* ignore */ } finally {
    memoryLoading.value = false;
  }
}

function startEditMemory(key: keyof Memory) {
  memoryDrafts.value[key] = memoryData.value[key] || "";
  memoryEditing.value[key] = true;
}

function cancelEditMemory(key: keyof Memory) {
  memoryEditing.value[key] = false;
}

async function saveMemory(key: keyof Memory) {
  memorySaving.value[key] = true;
  try {
    const updated = await memoryApi.update({ [key]: memoryDrafts.value[key] || null });
    memoryData.value = updated;
    memoryEditing.value[key] = false;
    ns.toast("已保存");
  } catch {
    ns.toast("保存失败", "error");
  } finally {
    memorySaving.value[key] = false;
  }
}

watch(tab, (t) => { if (t === "memory") loadMemory(); });
onMounted(() => { if (tab.value === "memory") loadMemory(); });

const notifyPrefs = reactive({
  mention: true,
  team_invite: true,
  project_update: true,
  agent_done: true,
  agent_error: true,
  system: false,
  email_digest: false,
  email_mention: true,
});
const notifyDirty = ref(false);
const notifySaving = ref(false);
watch(notifyPrefs, () => { notifyDirty.value = true; }, { deep: true });
async function saveNotifyPrefs() {
  notifySaving.value = true;
  try {
    await http.patch("/users/me", { notify_prefs: { ...notifyPrefs } });
    notifyDirty.value = false;
    ns.toast("通知偏好已保存");
  } catch {
    ns.toast("保存失败", "error");
  } finally {
    notifySaving.value = false;
  }
}
</script>

<template>
  <div class="stage">
    <div class="team-hero">
      <div class="team-hero-row">
        <div class="up-avatar" :style="{ background: form.color }">{{ auth.user?.initials || form.name.slice(0, 1) }}</div>
        <div class="team-info">
          <div class="team-crumb">个人设置 · PROFILE</div>
          <h1 class="team-name">{{ form.name }}<span class="handle">@{{ form.handle || "me" }}</span></h1>
          <div class="team-tagline">{{ form.title || "—" }}</div>
          <div class="team-meta-row">
            <span><Icon name="user" /> {{ auth.user?.email }}</span>
            <span class="role-pill">{{ auth.user?.role }}</span>
            <span><Icon name="globe" /> {{ auth.user?.source }}</span>
          </div>
        </div>
      </div>
      <div class="team-tabs">
        <button class="team-tab" :class="{ active: tab === 'profile' }" @click="tab = 'profile'">个人资料</button>
        <button class="team-tab" :class="{ active: tab === 'prefs' }" @click="tab = 'prefs'">偏好设置</button>
        <button class="team-tab" :class="{ active: tab === 'memory' }" @click="tab = 'memory'">代理记忆</button>
        <button class="team-tab" :class="{ active: tab === 'security' }" @click="tab = 'security'">安全</button>
        <button class="team-tab" :class="{ active: tab === 'notify' }" @click="tab = 'notify'">通知</button>
      </div>
    </div>

    <div class="team-body" >

      <!-- ── 个人资料 ── -->
      <template v-if="tab === 'profile'">
        <div class="section-card">
          <div class="section-head"><div class="section-title">基本资料</div></div>
          <div style="padding: 18px; display: grid; grid-template-columns: 140px 1fr; gap: 14px 18px; align-items: center; font-size: 13px">
            <div class="text-mute">姓名</div>
            <input class="cfg-input" v-model="form.name" />
            <div class="text-mute">用户名</div>
            <input class="cfg-input" v-model="form.handle" />
            <div class="text-mute">职位</div>
            <input class="cfg-input" v-model="form.title" />
            <div class="text-mute">部门</div>
            <input class="cfg-input" v-model="form.department" />
            <div class="text-mute">简介</div>
            <textarea class="cfg-input" style="height: 64px; padding-top: 8px" v-model="form.bio"></textarea>
            <div class="text-mute">头像颜色</div>
            <div class="up-swatches">
              <button v-for="c in COLORS" :key="c" class="up-sw" :class="{ active: form.color === c }" :style="{ background: c }" @click="form.color = c"></button>
            </div>
          </div>
        </div>
      </template>

      <!-- ── 偏好设置 ── -->
      <template v-else-if="tab === 'prefs'">
        <div class="section-card">
          <div class="section-head">
            <div class="section-title"><Icon name="bolt" /> 个人偏好记忆</div>
            <div class="text-mute-sm">AI 会在回答时参考你的偏好，让回复更贴合你的需求</div>
          </div>
          <div style="padding: 18px">
            <div v-for="(pref, idx) in prefsList" :key="idx" class="pref-row">
              <div class="pref-label">
                <input
                  v-if="pref.label === '自定义'"
                  class="cfg-input pref-key-input"
                  v-model="pref.key"
                  placeholder="偏好名称"
                  @input="onPrefChange"
                />
                <span v-else class="pref-key-label">{{ pref.label }}</span>
              </div>
              <input
                class="cfg-input pref-value-input"
                v-model="pref.value"
                :placeholder="pref.placeholder"
                @input="onPrefChange"
              />
              <button
                v-if="!PREF_TEMPLATES.find(t => t.key === pref.key)"
                class="btn-icon text-mute"
                style="flex-shrink: 0; padding: 4px"
                @click="removePref(idx)"
                title="删除"
              >✕</button>
            </div>

            <button class="btn" style="margin-top: 12px; font-size: 12px" @click="addCustomPref">
              + 添加自定义偏好
            </button>
          </div>
        </div>

        <div class="section-card" style="margin-top: 16px">
          <div class="section-head">
            <div class="section-title">界面偏好</div>
          </div>
          <div style="padding: 18px; font-size: 13px; color: var(--ink-mute)">
            主题、密度和语气风格可在右上角 <strong>Tweaks</strong> 面板中实时调整，更改会自动保存到本地。
          </div>
        </div>

        <div class="section-card" style="margin-top: 16px">
          <div class="section-head"><div class="section-title">语言与时区</div></div>
          <div style="padding: 18px; display: grid; grid-template-columns: 140px 1fr; gap: 14px 18px; align-items: center; font-size: 13px">
            <div class="text-mute">界面语言</div>
            <select class="cfg-input" style="height: 34px">
              <option value="zh">中文（简体）</option>
              <option value="en">English</option>
            </select>
            <div class="text-mute">时区</div>
            <input class="cfg-input text-mute" value="Asia/Shanghai (UTC+8)" readonly />
          </div>
        </div>

        <div v-if="prefsDirty" style="margin-top: 16px; display: flex; align-items: center; gap: 12px">
          <button class="btn primary" :disabled="prefsSaving" @click="savePrefs">
            {{ prefsSaving ? '保存中…' : '保存偏好记忆' }}
          </button>
          <span class="text-mute-sm">有未保存的更改</span>
        </div>
      </template>

      <!-- ── 代理记忆 ── -->
      <template v-else-if="tab === 'memory'">
        <div v-if="memoryLoading" style="padding: 32px; text-align: center; color: var(--ink-mute); font-size: 13px">加载中…</div>
        <template v-else>
          <div v-for="sec in MEMORY_SECTIONS" :key="sec.key" class="section-card" style="margin-bottom: 16px">
            <div class="section-head" style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
              <div>
                <div class="section-title">{{ sec.label }}</div>
                <div class="text-mute-sm" style="margin-top:2px">{{ sec.desc }}</div>
              </div>
              <button v-if="!memoryEditing[sec.key]" class="btn" style="font-size:12px;flex-shrink:0" @click="startEditMemory(sec.key)">
                编辑
              </button>
              <div v-else style="display:flex;gap:6px;flex-shrink:0">
                <button class="btn primary" style="font-size:12px" :disabled="memorySaving[sec.key]" @click="saveMemory(sec.key)">
                  {{ memorySaving[sec.key] ? '保存中…' : '保存' }}
                </button>
                <button class="btn" style="font-size:12px" @click="cancelEditMemory(sec.key)">取消</button>
              </div>
            </div>
            <div style="padding: 0 18px 18px">
              <template v-if="memoryEditing[sec.key]">
                <textarea
                  class="cfg-input"
                  style="width: 100%; min-height: 120px; padding-top: 8px; resize: vertical"
                  v-model="memoryDrafts[sec.key]"
                  :placeholder="sec.placeholder"
                ></textarea>
              </template>
              <div v-else-if="memoryData[sec.key]" class="memory-view-text">{{ memoryData[sec.key] }}</div>
              <div v-else class="memory-empty" @click="startEditMemory(sec.key)">
                <span>{{ sec.placeholder }}</span>
                <span class="memory-empty-hint">点击编辑</span>
              </div>
            </div>
          </div>
        </template>
      </template>

      <!-- ── 安全 ── -->
      <template v-else-if="tab === 'security'">
        <div class="section-card">
          <div class="section-head"><div class="section-title">两步验证 (2FA)</div></div>
          <div style="padding: 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px">
            <div>
              <div style="font-size: 13.5px; font-weight: 500; color: var(--ink)">{{ twoFaEnabled ? "已启用" : "未启用" }}</div>
              <div style="font-size: 12px; color: var(--ink-mute); margin-top: 3px">通过 TOTP 应用（Google Authenticator / Authy）保护账号。</div>
            </div>
            <button class="btn" :class="{ primary: !twoFaEnabled }" @click="twoFaEnabled = !twoFaEnabled">
              {{ twoFaEnabled ? "关闭 2FA" : "启用 2FA" }}
            </button>
          </div>
        </div>

        <div class="section-card" style="margin-top: 16px">
          <div class="section-head">
            <div class="section-title">登录会话</div>
            <span style="font-size: 11.5px; color: var(--ink-mute)">{{ sessions.length }} 个活跃设备</span>
          </div>
          <div class="section-body flush">
            <div v-for="s in sessions" :key="s.id" class="row-item" style="padding: 12px 16px">
              <Icon name="globe" style="color: var(--ink-mute); flex-shrink: 0" />
              <div class="flex-1-min">
                <div style="font-size: 13px; font-weight: 500; color: var(--ink)">
                  {{ s.device }}
                  <span v-if="s.current" style="margin-left: 6px; font-size: 10.5px; background: var(--accent-tint); color: var(--accent-deep); border-radius: 4px; padding: 1px 5px; font-weight: 600">当前</span>
                </div>
                <div style="font-size: 11.5px; color: var(--ink-mute); margin-top: 2px">{{ s.ip }} · {{ relTime(s.ts) }}</div>
              </div>
              <button v-if="!s.current" class="btn text-danger" @click="revokeSession(s.id)">撤销</button>
            </div>
          </div>
        </div>

        <div class="section-card" style="margin-top: 16px; border-color: color-mix(in srgb, var(--danger) 25%, var(--rule))">
          <div class="section-head"><div class="section-title text-danger">危险操作</div></div>
          <div style="padding: 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px">
            <div>
              <div style="font-size: 13px; font-weight: 500; color: var(--ink)">修改密码</div>
              <div class="text-mute-sm" style="margin-top:2px">需要验证当前密码。</div>
            </div>
            <button class="btn">修改密码</button>
          </div>
        </div>
      </template>

      <!-- ── 通知 ── -->
      <template v-else-if="tab === 'notify'">
        <div class="section-card">
          <div class="section-head"><div class="section-title"><Icon name="bolt" /> 站内通知</div></div>
          <div style="padding: 6px 0">
            <div v-for="(label, key) in { mention: '被@提及', team_invite: '团队邀请', project_update: '项目动态', agent_done: 'Agent 任务完成', agent_error: 'Agent 错误报警', system: '系统公告' }"
              :key="key" class="up-toggle-row">
              <div>
                <div class="up-toggle-nm">{{ label }}</div>
              </div>
              <label class="cfg-toggle-wrap">
                <input type="checkbox" v-model="(notifyPrefs as any)[key]" style="display:none" />
                <span class="cfg-toggle" :class="{ on: (notifyPrefs as any)[key] }" @click="(notifyPrefs as any)[key] = !(notifyPrefs as any)[key]"></span>
              </label>
            </div>
          </div>
        </div>

        <div class="section-card" style="margin-top: 16px">
          <div class="section-head"><div class="section-title"><Icon name="globe" /> 邮件通知</div></div>
          <div style="padding: 6px 0">
            <div class="up-toggle-row">
              <div><div class="up-toggle-nm">被@提及时发邮件</div><div class="up-toggle-ds">仅当你不在线时</div></div>
              <label class="cfg-toggle-wrap">
                <input type="checkbox" v-model="notifyPrefs.email_mention" style="display:none" />
                <span class="cfg-toggle" :class="{ on: notifyPrefs.email_mention }" @click="notifyPrefs.email_mention = !notifyPrefs.email_mention"></span>
              </label>
            </div>
            <div class="up-toggle-row">
              <div><div class="up-toggle-nm">每日摘要邮件</div><div class="up-toggle-ds">汇总前一天的活动，每天早 9 点发送</div></div>
              <label class="cfg-toggle-wrap">
                <input type="checkbox" v-model="notifyPrefs.email_digest" style="display:none" />
                <span class="cfg-toggle" :class="{ on: notifyPrefs.email_digest }" @click="notifyPrefs.email_digest = !notifyPrefs.email_digest"></span>
              </label>
            </div>
          </div>
        </div>

        <div v-if="notifyDirty" style="margin-top: 16px; display: flex; align-items: center; gap: 12px">
          <button class="btn primary" :disabled="notifySaving" @click="saveNotifyPrefs">{{ notifySaving ? "保存中…" : "保存偏好" }}</button>
          <span class="text-mute-sm">有未保存的更改</span>
        </div>
      </template>

    </div>

    <Transition name="savebar">
      <div v-if="dirty && tab === 'profile'" class="up-savebar">
        <Icon name="bolt" :size="14" /> 有未保存的更改
        <button class="btn" @click="save" :disabled="saving" style="color: var(--bg-canvas); border-color: rgba(255,255,255,0.3)">{{ saving ? "保存中…" : "保存" }}</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.savebar-enter-active,
.savebar-leave-active {
  transition: opacity 180ms, transform 180ms;
}
.savebar-enter-from,
.savebar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(12px);
}
.up-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--rule);
  gap: 12px;
}
.up-toggle-row:last-child { border-bottom: none }
.up-toggle-nm { font-size: 13px; font-weight: 500; color: var(--ink) }
.up-toggle-ds { font-size: 11.5px; color: var(--ink-mute); margin-top: 2px }
.cfg-toggle-wrap { flex-shrink: 0; cursor: pointer }
.cfg-toggle {
  display: inline-block;
  width: 36px; height: 20px;
  background: var(--rule);
  border-radius: 999px;
  position: relative;
  transition: background 200ms;
}
.cfg-toggle::after {
  content: "";
  position: absolute;
  top: 3px; left: 3px;
  width: 14px; height: 14px;
  background: #fff;
  border-radius: 50%;
  transition: transform 200ms;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.cfg-toggle.on { background: var(--accent) }
.cfg-toggle.on::after { transform: translateX(16px) }
.pref-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.pref-label {
  flex-shrink: 0;
  width: 110px;
}
.pref-key-label {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink);
  line-height: 32px;
}
.pref-key-input {
  font-size: 12.5px !important;
  height: 32px !important;
}
.pref-value-input {
  flex: 1;
  font-size: 12.5px !important;
  height: 32px !important;
}
.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  border-radius: 4px;
  transition: background 120ms;
}
.btn-icon:hover {
  background: var(--rule);
}
.memory-view-text {
  font-size: 13px;
  color: var(--ink);
  white-space: pre-wrap;
  line-height: 1.6;
  padding: 4px 0;
}
.memory-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border: 1px dashed var(--rule);
  border-radius: 8px;
  cursor: pointer;
  gap: 8px;
  transition: border-color 150ms;
}
.memory-empty:hover { border-color: var(--accent); }
.memory-empty > span:first-child { font-size: 12.5px; color: var(--ink-mute); }
.memory-empty-hint { font-size: 11.5px; color: var(--accent); flex-shrink: 0; }
</style>
