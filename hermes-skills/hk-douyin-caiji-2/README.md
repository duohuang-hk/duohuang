# hk-douyin-caiji-2

抖音视频采集 Hermes Agent Skill v2

## 功能

- 手动模式：丢抖音链接 → TikHub API 拉数据 → ASR（Groq Whisper）转口语文案 → 评论抓取 → 写飞书Base
- 监控模式：cron 每6小时自动博主新视频
- 19个字段：口播文案、语音转文字、高赞评论、评论摘录、粉丝数、时长等
- 自动建博主表 + 字段同步 + 去重

## 安装

```bash
# 将 skill 复制到 Hermes skills 目录
cp -r hk-douyin-caiji-2 ~/.hermes/skills/

# 将脚本复制到 scripts 目录
cp scripts/* ~/.hermes/scripts/

# 创建监控清单文件（空）
echo '{"bloggers":[]}' > ~/.hermes/data/douyin_monitor.json
```

## 依赖

- TikHub API Token（~/.openclaw/config.json）
- Groq API Key（同上）
- lark-cli v1.0.43+
- 飞书 Base：QBipbH886a95tysX4axcb73LnJf（抖音文案分析）

## 使用

在 Hermes 对话中丢抖音链接即可自动触发采集。
