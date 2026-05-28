#!/bin/bash
# 抖音监控采集 - Cron 定时任务脚本
# 读取监控清单，逐个博主检查新视频，同步到飞书

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONITOR_SCRIPT="${SCRIPT_DIR}/douyin_monitor.py"
SCRAPER_SCRIPT="${SCRIPT_DIR}/douyin_scraper.py"

# 获取监控清单
BLOGGERS=$(python3 "${MONITOR_SCRIPT}" list 2>&1)
HAS_BLOGGERS=$(echo "$BLOGGERS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('bloggers',[])))" 2>/dev/null)

if [ "$HAS_BLOGGERS" = "" ] || [ "$HAS_BLOGGERS" = "0" ]; then
    echo '{"ok": true, "msg": "监控清单为空，跳过"}'
    exit 0
fi

echo "开始监控采集: $(date)"

# 逐个博主采集
python3 "${MONITOR_SCRIPT}" list 2>&1 | python3 -c "
import json, subprocess, sys

d = json.load(sys.stdin)
bloggers = d.get('bloggers', [])
results = []

for b in bloggers:
    name = b['name']
    sec_uid = b['sec_uid']
    print(f'采集 {name}...')
    r = subprocess.run([
        'python3', '/Users/huangkundeclaw/.hermes/scripts/douyin_scraper.py',
        sec_uid, '--mode', 'batch'
    ], capture_output=True, text=True, timeout=120)
    try:
        result = json.loads(r.stdout)
        if result.get('ok'):
            new_count = result.get('new', 0)
            print(f'  {name}: 新增{new_count}条')
            results.append({'name': name, 'new': new_count})
        else:
            print(f'  {name}: 失败 - {result.get(\"error\", r.stdout[:100])}')
            results.append({'name': name, 'error': result.get('error', '?')})
    except:
        print(f'  {name}: 解析失败 - {r.stdout[:100]}')
        results.append({'name': name, 'error': 'parse fail'})

print()
print(json.dumps({'ok': True, 'results': results}, ensure_ascii=False))
" 2>&1