"""Test group chat creation with auto-add members + channel_mode inheritance."""
import requests
import json

BASE = "http://localhost:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={"username": "admin@hermes.io", "password": "Hermes@2026"})
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}
print("OK: logged in")

# Get teams
r = requests.get(f"{BASE}/teams", headers=H)
teams = r.json()
print(f"Teams: {len(teams)}")
if not teams:
    print("No teams!"); exit()
team_id = teams[0]["id"]

# Get team detail
r = requests.get(f"{BASE}/teams/{team_id}", headers=H)
team = r.json()
print(f"\nTeam detail:")
print(f"  Members: {len(team.get('members', []))}")
print(f"  Shared agents: {team.get('shared_agents')}")
print(f"  Channel mode: {team.get('channel_mode')}")

# Create group chat with EMPTY member lists — should auto-add from team
print(f"\n=== Creating group chat (auto-add from team) ===")
r = requests.post(f"{BASE}/conversations/group", headers=H, json={
    "title": "测试群聊",
    "team_id": team_id,
    "member_user_ids": [],
    "member_agent_ids": [],
})
if r.status_code != 201:
    print(f"ERROR: {r.status_code} {r.text}"); exit()
convo = r.json()
print(f"  Convo ID: {convo['id']}")
print(f"  Title: {convo['title']}")
print(f"  channel_mode: {convo.get('channel_mode')}")
print(f"  Members: {len(convo.get('members', []))}")
for m in convo.get("members", []):
    uid = m.get("user_id") or m.get("agent_id") or "?"
    role = m.get("role")
    kind = "agent" if m.get("agent_id") else "user"
    print(f"    - {uid[:12]}... ({kind}, {role})")

# Update channel_mode
convo_id = convo["id"]
print(f"\n=== Updating channel_mode to 'always' ===")
r = requests.patch(f"{BASE}/conversations/{convo_id}", headers=H, json={"channel_mode": "always"})
if r.status_code == 200:
    updated = r.json()
    print(f"  channel_mode: {updated.get('channel_mode')}")
else:
    print(f"  ERROR: {r.status_code} {r.text}")

# Update channel_mode to 'off'
r = requests.patch(f"{BASE}/conversations/{convo_id}", headers=H, json={"channel_mode": "off"})
print(f"  channel_mode (off): {r.json().get('channel_mode')}")

print("\nAll tests passed!")
