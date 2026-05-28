---
name: douyin-scraper
description: |
  抖音视频采集工具。从抖音链接提取完整视频数据（口播ASR文案、评论、作者信息、互动数据），写入飞书多维表格。

  使用场景：
  (1) 用户丢来 douyin.com 或 v.douyin.com 链接
  (2) 需要分析抖音视频的口播内容、评论、数据
  (3) 需要监控博主的新视频发布
  (4) 需要将抖音数据整理到飞书表格

  注意：本 skill 需要 TikHub API Token 和 Groq API Key（在 ~/.openclaw/config.json 中），以及飞书多维表格「抖音文案分析」（Base Token: QBipbH886a95tysX4axcb73LnJf）

  安装依赖：
  - pip install tikhub (或使用内置的 curl + Python subprocess)
  - brew install ffmpeg（用于 ASR 音频处理）
  - npm install -g @larksuiteio/cli（飞书 CLI，用于写入数据）
---

# 抖音视频采集 Skill

## 核心脚本

```
~/.codex/skills/douyin-scraper/scripts/
  douyin_scraper.py     # 主采集脚本
  douyin_monitor.py     # 监控清单管理
  douyin_cron.sh        # Cron 定时任务
```

## 使用方式

### 1. 手动采集单条视频

```python
python3 ~/.codex/skills/douyin-scraper/scripts/douyin_scraper.py "https://www.douyin.com/video/xxxxx"
```

可选参数：
- `--no-asr`：跳过语音转文字（快速模式）
- `--mode batch`：批量采集博主所有视频

### 2. 博主监控

```python
# 添加博主到监控
python3 ~/.codex/skills/douyin-scraper/scripts/douyin_monitor.py add "博主名" "sec_uid"

# 查看监控清单
python3 ~/.codex/skills/douyin-scraper/scripts/douyin_monitor.py list

# 移除监控
python3 ~/.codex/skills/douyin-scraper/scripts/douyin_monitor.py remove "sec_uid"
```

### 3. 采集字段（写入飞书）

| 字段 | 说明 |
|------|------|
| 视频标题 | 标题+话题标签 |
| 视频文案 | ASR 口播转写内容 |
| 语音转文字 | ASR 结果 |
| 作者昵称/粉丝数 | 博主信息 |
| 点赞/评论/转发/收藏 | 互动数据 |
| 时长(分钟) | 精确到0.1分钟 |
| 高赞评论 | Top 5 评论 |
| 评论摘录 | 全部评论 |
| 话题标签 | 提取的 hashtag |

## 数据流程

```
抖音链接 → TikHub API 拉元数据 → ASR(Groq Whisper) 转口播 → 评论抓取 → 写入飞书 Base
```

## 依赖

- TikHub API Token（~/.openclaw/config.json）
- Groq API Key（~/.openclaw/config.json）
- lark-cli（飞书数据写入）
- ffmpeg（ASR 音频处理）
- 代理 http://127.0.0.1:7890（TikHub 访问）
- 飞书 Base: QBipbH886a95tysX4axcb73LnJf
