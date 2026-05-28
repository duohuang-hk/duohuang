#!/usr/bin/env python3
import json, os, subprocess, sys, time
from datetime import datetime

BASE_TOKEN = "QBipbH886a95tysX4axcb73LnJf"
_TPL_TABLE = "tblBKSKeEOmLV3ly"
TIKHUB_BASE = "https://api.tikhub.io"

def get_token():
    with open(os.path.expanduser("~/.openclaw/config.json")) as f:
        return json.load(f)["tikhub_api_token"]

def tikhub_get(path, params):
    qs = "&".join(k + "=" + v for k, v in params.items())
    url = TIKHUB_BASE + path + "?" + qs
    tk = get_token()
    hdr = "Authorization: Bearer " + tk
    
    def _do_request(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except:
                return None
        return None
    
    # Try without proxy first (Codex sandbox, direct network)
    direct = _do_request(["curl", "-s", "--max-time", "15", url, "-H", hdr])
    if direct is not None:
        return direct
    
    # Fall back to proxy
    proxy_req = _do_request(["curl", "-s", "--max-time", "15", "--proxy", "http://127.0.0.1:7890", url, "-H", hdr])
    if proxy_req is not None:
        return proxy_req
    
    return {"error": "curl failed (tried direct + proxy)"}

def lark(args):
    r = subprocess.run(["lark-cli"] + args, capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout)
    except:
        return {"ok": False}

def template_fields():
    r = lark(["base", "+field-list", "--base-token", BASE_TOKEN, "--table-id", _TPL_TABLE])
    return r.get("data", {}).get("fields", [])

def sync_fields(tid, tpl_fs):
    r = lark(["base", "+field-list", "--base-token", BASE_TOKEN, "--table-id", tid])
    exist = {f["name"] for f in r.get("data", {}).get("fields", [])}
    for f in tpl_fs:
        if f["name"] == "ID":
            continue
        if f["name"] not in exist:
            j = json.dumps({"name": f["name"], "type": f["type"], "style": f.get("style", {})}, ensure_ascii=False)
            lark(["base", "+field-create", "--base-token", BASE_TOKEN, "--table-id", tid, "--json", j])

def fetch_video(url):
    data = tikhub_get("/api/v1/douyin/app/v3/fetch_one_video_by_share_url", {"share_url": url})
    if data.get("code") != 200:
        return None, "API: " + data.get("message", data.get("error", "?"))
    ad = data.get("data", {}).get("aweme_detail")
    if not ad:
        return None, "empty data"
    return ad, None

_TMP_AUDIO_DIR = "/tmp/douyin_audio"

def ensure_tmp():
    os.makedirs(_TMP_AUDIO_DIR, exist_ok=True)

def get_music_url(ad):
    """从aweme_detail中提取音频URL（原声）"""
    music = ad.get("music", {})
    play_url = music.get("play_url", {})
    if isinstance(play_url, dict):
        ul = play_url.get("url_list", [])
        if ul:
            return ul[0]
    return None

def transcribe(music_url, aweme_id):
    """下载音频→Groq Whisper 转文字"""
    groq_key = None
    try:
        with open(os.path.expanduser("~/.openclaw/config.json")) as f:
            groq_key = json.load(f).get("groq_api_key")
    except:
        pass
    if not groq_key:
        return None, "无Groq API Key"
    
    # Download audio - try direct first, fall back to proxy
    audio_path = os.path.join(_TMP_AUDIO_DIR, aweme_id + ".mp3")
    dl_cmds = [
        ["curl", "-s", "--max-time", "30", "-o", audio_path, music_url],
        ["curl", "-s", "--max-time", "30", "--proxy", "http://127.0.0.1:7890", "-o", audio_path, music_url],
    ]
    dl_ok = False
    for dl_cmd in dl_cmds:
        dl = subprocess.run(dl_cmd, timeout=60)
        if dl.returncode == 0 and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            dl_ok = True
            break
    if not dl_ok:
        return None, "下载音频失败"
    
    try:
        # Send to Groq Whisper - try direct first, fall back to proxy
        whisper_cmds = [
            ["curl", "-s", "--max-time", "180",
             "https://api.groq.com/openai/v1/audio/transcriptions",
             "-H", "Authorization: Bearer " + groq_key,
             "-F", "file=@" + audio_path,
             "-F", "model=whisper-large-v3",
             "-F", "language=zh"],
            ["curl", "-s", "--max-time", "180", "--proxy", "http://127.0.0.1:7890",
             "https://api.groq.com/openai/v1/audio/transcriptions",
             "-H", "Authorization: Bearer " + groq_key,
             "-F", "file=@" + audio_path,
             "-F", "model=whisper-large-v3",
             "-F", "language=zh"],
        ]
        text = None
        for wcmd in whisper_cmds:
            r = subprocess.run(wcmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                try:
                    result = json.loads(r.stdout)
                    t = result.get("text", "")
                    if t.strip():
                        text = t.strip()
                        break
                except:
                    pass
        if text:
            return text, None
        return None, "ASR返回空文本"
    except Exception as e:
        return None, "ASR失败: " + str(e)[:100]
    finally:
        # Cleanup
        try:
            os.remove(audio_path)
        except:
            pass

def fetch_user_profile(sec_uid):
    """获取博主真实资料（粉丝数等）"""
    if not sec_uid:
        return {}
    data = tikhub_get("/api/v1/douyin/web/handler_user_profile_v4", {"sec_user_id": sec_uid})
    if data.get("code") != 200:
        return {}
    return data.get("data", {}).get("user", {}) or {}

def fetch_comments(aweme_id, count=30):
    """获取视频评论，返回(高赞评论列表, 全部评论文本)"""
    data = tikhub_get("/api/v1/douyin/app/v3/fetch_video_comments", {
        "aweme_id": aweme_id, "cursor": "0", "count": str(count)
    })
    if data.get("code") != 200:
        return [], ""
    
    comments = data.get("data", {}).get("comments", [])
    if not comments:
        return [], ""
    
    # 按点赞排序
    sorted_c = sorted(comments, key=lambda x: x.get("digg_count", 0), reverse=True)
    
    # 高赞评论（前5条）
    hot = []
    for c in sorted_c[:5]:
        u = c.get("user", {})
        nick = u.get("nickname", "?")
        text = c.get("text", "")
        digg = c.get("digg_count", 0)
        hot.append(nick + ": " + text + "  [👍" + str(digg) + "]")
    
    # 全部评论汇总
    all_text = "\n".join([
        c.get("user", {}).get("nickname", "?") + ": " + c.get("text", "")
        for c in comments
    ])
    
    return hot, all_text

def extract(ad, asr_text=None, comments=None, profile=None):
    s, a = ad.get("statistics", {}), ad.get("author", {})
    tags = [t.get("hashtag_name") for t in ad.get("text_extra", []) if t.get("hashtag_name")]
    ct = ad.get("create_time", 0)
    desc_text = ad.get("desc", "")
    real_fans = profile.get("follower_count") if profile else None
    return {
        "视频标题": desc_text, "视频链接": ad.get("share_url", ""),
        "aweme_id": ad.get("aweme_id", ""), "作者昵称": a.get("nickname", ""),
        "作者sec_uid": a.get("sec_uid", ""), "作者粉丝数": real_fans or a.get("follower_count", 0) or 0,
        "作者签名": a.get("signature", ""),
        "发布时间": datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M") if ct else "",
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "时长(分钟)": round((ad.get("duration", 0) or 0) / 60000, 1),
        "点赞数": s.get("digg_count", 0) or 0, "评论数": s.get("comment_count", 0) or 0,
        "转发数": s.get("share_count", 0) or 0, "收藏数": s.get("collect_count", 0) or 0,
        "话题标签": "、".join(tags),
        "视频文案": asr_text or desc_text,
        "语音转文字": asr_text or "",
        "评论摘录": comments[1] if comments and comments[1] else "",
        "高赞评论": "\n\n".join(comments[0]) if comments and comments[0] else "",
    }

def ensure_table(author, sec_uid):
    name = author or ("博主_" + sec_uid[-8:] if sec_uid else "未知博主")
    tpl = template_fields()
    r = lark(["base", "+table-list", "--base-token", BASE_TOKEN])
    for t in r.get("data", {}).get("tables", []):
        if t["name"] == name:
            sync_fields(t["id"], tpl)
            return t["id"], None
    r = lark(["base", "+table-create", "--base-token", BASE_TOKEN, "--name", name])
    tid = r.get("data", {}).get("table", {}).get("id")
    if not tid:
        return None, "create fail"
    for f in tpl:
        if f["name"] == "ID":
            continue
        lark(["base", "+field-create", "--base-token", BASE_TOKEN, "--table-id", tid,
              "--json", json.dumps({"name": f["name"], "type": f["type"], "style": f.get("style", {})}, ensure_ascii=False)])
    return tid, None

def check_dup(tid, aid):
    j = json.dumps({"keyword": str(aid), "search_fields": ["aweme_id"], "limit": 1}, ensure_ascii=False)
    r = lark(["base", "+record-search", "--base-token", BASE_TOKEN, "--table-id", tid, "--json", j, "--format", "json"])
    return len(r.get("data", {}).get("records", [])) > 0

def write_rec(tid, f):
    lark(["base", "+record-upsert", "--base-token", BASE_TOKEN, "--table-id", tid, "--json", json.dumps(f, ensure_ascii=False)])

def run_batch(sec_uid):
    """监控模式：提取某个博主的最新视频，自动同步到飞书"""
    data = tikhub_get("/api/v1/douyin/app/v3/fetch_user_post_videos", {
        "sec_user_id": sec_uid, "count": "10"
    })
    if data.get("code") != 200:
        return {"ok": False, "error": "API: " + data.get("message", data.get("error", "?"))}
    aweme_list = data.get("data", {}).get("aweme_list", [])
    if not aweme_list:
        return {"ok": False, "error": "no videos"}
    
    results = []
    for ad in aweme_list:
        f = extract(ad)
        author = f["作者昵称"] or "?"
        tid, err = ensure_table(author, f["作者sec_uid"])
        if err:
            results.append({"id": f["aweme_id"], "status": "error", "msg": err})
            continue
        if check_dup(tid, f["aweme_id"]):
            results.append({"id": f["aweme_id"], "status": "dup"})
            continue
        write_rec(tid, f)
        results.append({"id": f["aweme_id"], "status": "new"})
    
    return {"ok": True, "total": len(aweme_list), "new": sum(1 for r in results if r["status"] == "new"), "results": results}

def run(url, do_asr=True):
    # Parse URL: if it's a user profile with modal_id, extract the video ID
    import urllib.parse as up
    parsed = up.urlparse(url)
    if "modal_id=" in url:
        qs = up.parse_qs(parsed.query)
        vid = qs.get("modal_id", [None])[0]
        if vid:
            url = "https://www.douyin.com/video/" + vid
    elif parsed.path and "/video/" in parsed.path:
        pass  # already a valid video URL
    elif parsed.path and parsed.path.split("/")[-1].isdigit():
        # path ends with a video ID
        pass
    
    ad, err = fetch_video(url)
    if err:
        return {"ok": False, "error": err}
    
    # ASR
    asr_text = None
    if do_asr:
        music_url = get_music_url(ad)
        if music_url:
            asr_text, asr_err = transcribe(music_url, ad.get("aweme_id", "0"))
            if asr_err:
                return {"ok": False, "error": "ASR: " + asr_err}
    
    # Comments
    comments = None
    aweme_id = ad.get("aweme_id", "")
    if aweme_id:
        try:
            comments = fetch_comments(aweme_id)
        except:
            pass
    
    # User profile (for real follower count)
    profile = None
    sec_uid = ad.get("author", {}).get("sec_uid", "")
    if sec_uid:
        try:
            profile = fetch_user_profile(sec_uid)
        except:
            pass
    
    f = extract(ad, asr_text, comments, profile)
    author = f["作者昵称"] or "?"
    tid, err = ensure_table(author, f["作者sec_uid"])
    if err:
        return {"ok": False, "error": err}
    if check_dup(tid, f["aweme_id"]):
        return {"ok": True, "dup": True, "author": author, "id": f["aweme_id"]}
    write_rec(tid, f)
    title = f["视频文案"][:60] if len(f["视频文案"]) > 60 else f["视频文案"]
    return {"ok": True, "author": author, "id": f["aweme_id"], "title": title, "asr": bool(asr_text)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "usage: script.py <url|sec_uid> [--mode single|batch] [--no-asr]"}))
        sys.exit(1)
    
    mode = "single"
    do_asr = True
    if "--mode" in sys.argv:
        mi = sys.argv.index("--mode")
        mode = sys.argv[mi + 1] if mi + 1 < len(sys.argv) else "single"
    if "--no-asr" in sys.argv:
        do_asr = False
    
    if mode == "batch":
        print(json.dumps(run_batch(sys.argv[1]), ensure_ascii=False))
    else:
        print(json.dumps(run(sys.argv[1], do_asr), ensure_ascii=False))
