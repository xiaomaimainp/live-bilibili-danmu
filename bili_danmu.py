import argparse
import json
import logging
import os
import random
import sys
import time
import urllib.parse

import requests

# B站登录失效相关错误码
LOGIN_EXPIRED_CODES = {-101, -111, -400, 1001001}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bili-danmu")


def load_config(config_path):
    """从配置文件加载设置，凭据可被环境变量覆盖（优先级：环境变量 > 配置文件）。"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("配置文件 %s 不存在，请参考 config.example.json 创建", config_path)
        return None
    except json.JSONDecodeError as e:
        logger.error("配置文件 %s 格式错误: %s", config_path, e)
        return None
    except Exception as e:
        logger.error("读取配置文件时出错: %s", e)
        return None

    # 环境变量优先级高于配置文件，避免把敏感凭据写进 git
    config["csrf"] = os.environ.get("BILI_CSRF", config.get("csrf"))
    sessdata = os.environ.get("BILI_SESSDATA", config.get("sessdata"))
    # SESSDATA 可能以 URL 编码形式（%2C/%2A）保存，统一解码为真实字符
    config["sessdata"] = urllib.parse.unquote(sessdata) if sessdata else sessdata
    return config


def default_config():
    """返回一份默认配置模板。"""
    return {
        "room_ids": [0, 0],
        "message": "自己手动输入",
        "csrf": "替换为你的bili_jct",
        "sessdata": "替换为你的SESSDATA",
        "interval": 20,
        "jitter": 5,
    }


def ensure_config(config_path):
    """配置不存在时按默认模板创建，返回加载后的配置。"""
    if not os.path.exists(config_path):
        logger.warning("配置文件 %s 不存在，已创建默认模板，请按提示填写凭据", config_path)
        save_config(default_config(), config_path)
    return load_config(config_path)


def save_config(config, config_path):
    """将配置写入文件（不存在则创建），失败时返回 False。"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info("配置已写入: %s", config_path)
        return True
    except Exception as e:
        logger.error("写入配置文件失败 %s: %s", config_path, e)
        return False


def parse_cookie_string(cookie_str):
    """
    从整段 Cookie 字符串中解析出 SESSDATA 与 bili_jct(csrF)。
    支持两种格式：
      - 分号分隔:  SESSDATA=xxx; bili_jct=yyy; ...
      - Netscape 文本: 每行 domain\tflag\tpath\tsecure\texp\tname\tvalue
    返回 {'csrf': ..., 'sessdata': ...}，缺失的字段为 None。
    """
    cookie_str = (cookie_str or "").strip()
    if not cookie_str:
        return {"csrf": None, "sessdata": None}

    found = {"SESSDATA": None, "bili_jct": None}

    # 优先按分号分隔解析
    if ";" in cookie_str or "=" in cookie_str and "\t" not in cookie_str:
        for part in cookie_str.split(";"):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in found:
                found[k] = v

    # 兼容 Netscape cookie 文本格式（按行，末两列为 name/value）
    if found["SESSDATA"] is None or found["bili_jct"] is None:
        for line in cookie_str.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) >= 7:
                name, value = cols[-2], cols[-1]
                if name in found:
                    found[name] = value

    return {"csrf": found["bili_jct"], "sessdata": found["SESSDATA"]}


def validate_config(config):
    """校验配置完整性，返回有效房间 ID 列表或 None。"""
    if not config:
        return None

    csrf = config.get("csrf")
    sessdata = config.get("sessdata")
    if not csrf or not sessdata:
        logger.error("缺少 csrf 或 sessdata，请检查配置文件或环境变量 BILI_CSRF / BILI_SESSDATA")
        return None

    rooms = config.get("room_ids")
    if not isinstance(rooms, list) or not rooms:
        logger.error("room_ids 必须为非空列表")
        return None

    # 过滤无效房间（0、空、非数字），统一转整型
    valid_rooms = []
    for r in rooms:
        try:
            rid = int(r)
        except (TypeError, ValueError):
            logger.warning("忽略无效房间 ID: %r", r)
            continue
        if rid <= 0:
            logger.warning("忽略无效房间 ID: %s", rid)
            continue
        if rid not in valid_rooms:
            valid_rooms.append(rid)

    if not valid_rooms:
        logger.error("没有有效的房间 ID")
        return None

    message = (config.get("message") or "").strip()
    if not message:
        logger.error("弹幕内容 message 不能为空")
        return None

    return valid_rooms


def build_session(csrf, sessdata):
    """构造可复用的 Session，复用 TCP 连接并带好固定请求头。"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://live.bilibili.com/",
    })
    # 用 cookies.set 而非手动拼字符串，避免 sessdata 含逗号时被截断
    session.cookies.set("bili_jct", csrf, domain=".bilibili.com")
    session.cookies.set("SESSDATA", sessdata, domain=".bilibili.com")
    return session


def send_live_danmaku(session, room_id, message):
    """
    向B站直播间发送弹幕。返回 'ok' / 'retry' / 'fatal'。
    ok:     发送成功
    retry:  可下一轮重试的失败
    fatal:  登录失效等需停机错误
    """
    url = "https://api.live.bilibili.com/msg/send"
    data = {
        "roomid": room_id,
        "msg": message,
        "color": "16777215",  # 默认白色
        "fontsize": "25",
        "mode": "1",
        "rnd": str(int(time.time())),
        "csrf": session.cookies.get("bili_jct", ""),
        "csrf_token": session.cookies.get("bili_jct", ""),
    }

    try:
        response = session.post(url, data=data, timeout=10)
        result = response.json()
    except requests.RequestException as e:
        logger.warning("房间 %s 网络请求失败: %s", room_id, e)
        return "retry"
    except ValueError:
        logger.warning("房间 %s 返回非 JSON，可能被限流或接口异常", room_id)
        return "retry"

    code = result.get("code")
    if code == 0:
        logger.info("弹幕发送成功: %s (房间: %s)", message, room_id)
        return "ok"

    msg = result.get("message", "未知错误")
    if code in LOGIN_EXPIRED_CODES:
        logger.error("登录态失效 (code=%s, msg=%s)，请更新 csrf/sessdata 后重启", code, msg)
        return "fatal"

    logger.warning("弹幕发送失败 (房间 %s, code=%s): %s", room_id, code, msg)
    return "retry"


def run(room_ids, message, csrf, sessdata, interval, jitter):
    session = build_session(csrf, sessdata)

    logger.info("直播间ID列表: %s", room_ids)
    logger.info("弹幕内容: %s", message)
    logger.info("基础间隔: %ss，随机抖动: %ss", interval, jitter)
    logger.info("开始发送弹幕，按 Ctrl+C 停止")

    try:
        round_count = 0
        while True:
            round_count += 1
            logger.info("===== 第 %d 轮开始 =====", round_count)
            for room_id in room_ids:
                status = send_live_danmaku(session, room_id, message)
                if status == "fatal":
                    logger.error("检测到致命错误，停止发送")
                    return
                # 房间之间稍作延迟，避免请求过于频繁
                time.sleep(random.uniform(0.8, 1.5))
            wait = max(1, interval + random.uniform(-jitter, jitter))
            logger.info("本轮发送完成，等待 %.1f 秒后继续...", wait)
            time.sleep(wait)
    except KeyboardInterrupt:
        logger.info("弹幕发送已停止")


def parse_args():
    parser = argparse.ArgumentParser(description="B站直播弹幕自动发送工具")
    parser.add_argument(
        "-c", "--config",
        default=os.path.join(os.path.dirname(__file__), "config.json"),
        help="配置文件路径 (默认: 同目录 config.json)",
    )
    return parser.parse_args()


# 占位符/空值均视为未配置凭据
CREDENTIAL_PLACEHOLDERS = {"", "替换为你的bili_jct", "替换为你的SESSDATA"}


def credentials_missing(config):
    """csrf 或 sessdata 为空或仍为默认占位符时返回 True。"""
    csrf = (config.get("csrf") or "").strip()
    sessdata = (config.get("sessdata") or "").strip()
    return csrf in CREDENTIAL_PLACEHOLDERS or sessdata in CREDENTIAL_PLACEHOLDERS


def prompt_and_save_cookies(config, config_path):
    """
    交互式要求粘贴浏览器整段 Cookie，解析出 csrf/sessdata 后写回配置。
    返回更新后的 config；解析失败或用户跳过则返回原 config。
    """
    print("未检测到有效的 csrf / sessdata。")
    print("请粘贴浏览器复制的整段 Cookie（形如 SESSDATA=xxx; bili_jct=yyy; ...）：")
    try:
        cookie_input = input("Cookie> ").strip()
    except EOFError:
        logger.error("未读取到输入，仍以占位符运行（发送会失败）")
        return config

    creds = parse_cookie_string(cookie_input)
    if not creds["csrf"] or not creds["sessdata"]:
        logger.error("未能解析出 SESSDATA / bili_jct，请确认复制完整")
        return config

    config["csrf"] = creds["csrf"]
    config["sessdata"] = creds["sessdata"]
    if not save_config(config, config_path):
        return config
    logger.info("csrf / sessdata 已自动写入配置，请妥善保管 config.json")
    return config


def main():
    args = parse_args()

    config = ensure_config(args.config)
    if not config:
        sys.exit(1)

    # 凭据缺失时交互式获取并写回，其余配置保持不动
    if credentials_missing(config):
        config = prompt_and_save_cookies(config, args.config)

    room_ids = validate_config(config)
    if not room_ids:
        sys.exit(1)

    message = config["message"].strip()
    csrf = config["csrf"]
    sessdata = config["sessdata"]
    interval = max(1, int(config.get("interval", 20)))
    jitter = max(0, int(config.get("jitter", 5)))

    run(room_ids, message, csrf, sessdata, interval, jitter)


if __name__ == "__main__":
    main()
