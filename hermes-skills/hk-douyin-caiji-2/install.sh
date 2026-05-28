#!/bin/bash
# hk-douyin-caiji-2 一键安装脚本
# 用法: bash install.sh
# 在新电脑上运行，自动下载配置所有依赖

set -e

echo "========================================"
echo "  hk-douyin-caiji-2 安装脚本"
echo "  抖音视频采集 Hermes Skill"
echo "========================================"
echo ""

# ---------- 1. 检查 Hermes ----------
echo "[1/6] 检查 Hermes Agent..."
if ! command -v hermes &>/dev/null; then
    echo "  → 未检测到 Hermes，开始安装..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    echo "  ✓ Hermes 安装完成"
else
    echo "  ✓ Hermes 已安装 ($(hermes --version 2>&1 | head -1))"
fi

# ---------- 2. 下载 Skill ----------
echo "[2/6] 下载 hk-douyin-caiji-2..."
SKILL_DIR="$HOME/.hermes/skills/hk-douyin-caiji-2"
if [ -d "$SKILL_DIR" ]; then
    echo "  → 目录已存在，更新..."
    cd "$SKILL_DIR"
    git pull 2>/dev/null || true
else
    cd "$HOME/.hermes/skills"
    # 克隆整个仓库
    git clone --depth 1 https://github.com/huangkun7333-commits/duohuang.git /tmp/duohuang_install 2>/dev/null || true
    mkdir -p "$SKILL_DIR"
    if [ -d /tmp/duohuang_install ]; then
        cp -r /tmp/duohuang_install/hermes-skills/hk-douyin-caiji-2/* "$SKILL_DIR/"
        rm -rf /tmp/duohuang_install
    fi
fi
echo "  ✓ Skill 已下载到 $SKILL_DIR"

# ---------- 3. 复制脚本 ----------
echo "[3/6] 安装脚本..."
SCRIPTS_DIR="$HOME/.hermes/scripts"
mkdir -p "$SCRIPTS_DIR"
if [ -d "$SKILL_DIR/scripts" ]; then
    cp "$SKILL_DIR/scripts/"*.py "$SCRIPTS_DIR/" 2>/dev/null || true
    cp "$SKILL_DIR/scripts/"*.sh "$SCRIPTS_DIR/" 2>/dev/null || true
    chmod +x "$SCRIPTS_DIR/"*.sh 2>/dev/null || true
    echo "  ✓ 脚本已复制到 $SCRIPTS_DIR"
else
    echo "  ⚠️  未找到脚本目录，跳过"
fi

# ---------- 4. 检查依赖 ----------
echo "[4/6] 检查依赖..."
MISSING=""

# ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    MISSING="$MISSING ffmpeg"
fi

# lark-cli
if ! command -v lark-cli &>/dev/null; then
    MISSING="$MISSING lark-cli"
fi

if [ -n "$MISSING" ]; then
    echo "  ⚠️  缺失的依赖: $MISSING"
    echo "  → 请手动安装:"
    echo "    ffmpeg:  brew install ffmpeg"
    echo "    lark-cli: npm install -g @larksuiteio/cli"
else
    echo "  ✓ 所有依赖已满足"
fi

# ---------- 5. 配置环境 ----------
echo "[5/6] 配置文件..."

# 检查 config.json
CONFIG_FILE="$HOME/.openclaw/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    mkdir -p "$HOME/.openclaw"
    cat > "$CONFIG_FILE" << 'CONFEOF'
{
    "tikhub_api_token": "",
    "groq_api_key": ""
}
CONFEOF
    echo "  → 已创建 $CONFIG_FILE"
    echo "  ⚠️  请编辑 $CONFIG_FILE 填入 tikhub_api_token 和 groq_api_key"
else
    echo "  ✓ config.json 已存在"
fi

# 检查 .env 中的飞书配置
ENV_FILE="$HOME/.hermes/.env"
if [ ! -f "$ENV_FILE" ] || ! grep -q "FEISHU_APP_ID" "$ENV_FILE" 2>/dev/null; then
    cat >> "$ENV_FILE" << 'ENVEOF'

# 飞书机器人配置
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
FEISHU_ALLOW_ALL_USERS=true
FEISHU_GROUP_POLICY=open
ENVEOF
    echo "  → 请在 $ENV_FILE 中填入 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
else
    echo "  ✓ .env 飞书配置已存在"
fi

# 监控清单
MONITOR_FILE="$HOME/.hermes/data/douyin_monitor.json"
if [ ! -f "$MONITOR_FILE" ]; then
    mkdir -p "$HOME/.hermes/data"
    echo '{"bloggers":[]}' > "$MONITOR_FILE"
    echo "  ✓ 监控清单已创建"
fi

# ---------- 6. 注册 Cron ----------
echo "[6/6] 注册定时采集任务..."
if command -v hermes &>/dev/null; then
    # 先检查是否已存在
    EXISTING=$(hermes cron list 2>/dev/null | grep "抖音监控采集" || true)
    if [ -z "$EXISTING" ]; then
        hermes cron create "every 6h" \
            --name "抖音监控采集" \
            --script douyin_cron.sh \
            --no-agent \
            --deliver local \
            2>/dev/null || echo "  ⚠️  cron 注册失败（可手动执行）"
        echo "  ✓ 定时采集任务已注册（每6小时）"
    else
        echo "  ✓ 定时采集任务已存在"
    fi
fi

# ---------- 完成 ----------
echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "  使用前检查："
echo "  1. 编辑 ~/.openclaw/config.json 填入 TikHub Token"
echo "  2. 编辑 ~/.hermes/.env 填入飞书 App Secret"
echo "  3. 重启网关: hermes gateway restart"
echo "  4. 丢个抖音链接试试"
echo ""
echo "  更详细说明: $SKILL_DIR/README.md"
