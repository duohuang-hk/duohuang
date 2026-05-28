#!/usr/bin/env python3
"""博主监控清单管理 - 添加/移除/列出"""
import json, os, sys

MONITOR_FILE = os.path.expanduser("~/.hermes/data/douyin_monitor.json")

def load():
    if not os.path.exists(MONITOR_FILE):
        return {"bloggers": []}
    with open(MONITOR_FILE) as f:
        return json.load(f)

def save(data):
    os.makedirs(os.path.dirname(MONITOR_FILE), exist_ok=True)
    with open(MONITOR_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add(name, sec_uid):
    data = load()
    for b in data["bloggers"]:
        if b["sec_uid"] == sec_uid:
            return {"ok": False, "msg": "已在监控列表中: " + name}
    data["bloggers"].append({"name": name, "sec_uid": sec_uid})
    save(data)
    return {"ok": True, "msg": "已添加: " + name}

def remove(sec_uid):
    data = load()
    before = len(data["bloggers"])
    data["bloggers"] = [b for b in data["bloggers"] if b["sec_uid"] != sec_uid]
    if len(data["bloggers"]) == before:
        return {"ok": False, "msg": "未找到该博主"}
    save(data)
    return {"ok": True, "msg": "已移除"}

def list_all():
    data = load()
    if not data["bloggers"]:
        return {"ok": True, "bloggers": [], "msg": "监控清单为空"}
    return {"ok": True, "bloggers": data["bloggers"], "count": len(data["bloggers"])}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "usage: monitor.py <add|remove|list> [name] [sec_uid]"}))
        sys.exit(1)
    
    action = sys.argv[1]
    if action == "add" and len(sys.argv) >= 4:
        print(json.dumps(add(sys.argv[2], sys.argv[3]), ensure_ascii=False))
    elif action == "remove" and len(sys.argv) >= 3:
        print(json.dumps(remove(sys.argv[2]), ensure_ascii=False))
    elif action == "list":
        print(json.dumps(list_all(), ensure_ascii=False))
    else:
        print(json.dumps({"ok": False, "error": "参数错误"}))
