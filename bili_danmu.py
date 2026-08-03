import argparse
import json
import logging
import os
import random
import sys
import time

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
    config["sessdata"] = os.environ.get("BILI_SESSDATA", config.get("sessdata"))
    return config


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
        "Cookie": f"bili_jct={csrf}; SESSDATA={sessdata}",
    })
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


def main():
    args = parse_args()
    config = load_config(args.config)
    if not config:
        sys.exit(1)

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
