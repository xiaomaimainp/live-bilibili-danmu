import requests
import json
import time
import random
import os

def load_config():
    """从配置文件加载设置"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_file} 不存在，请创建配置文件")
        return None
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return None

def send_live_danmaku(room_id, message, csrf, sessdata):
    """
    向B站直播间发送弹幕
    
    参数:
        room_id: 直播间ID
        message: 弹幕内容
        csrf: B站CSRF令牌
        sessdata: B站会话数据
    """
    # B站直播弹幕API
    url = "https://api.live.bilibili.com/msg/send"
    
    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'bili_jct={csrf}; SESSDATA={sessdata}'
    }
    
    # 请求参数
    data = {
        'roomid': room_id,
        'msg': message,
        'color': '16777215',  # 默认白色
        'fontsize': '25',
        'mode': '1',
        'rnd': str(int(time.time())),
        'csrf': csrf,
        'csrf_token': csrf
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        
        if result['code'] == 0:
            print(f"弹幕发送成功: {message} (房间: {room_id})")
            return True
        else:
            print(f"弹幕发送失败 (房间: {room_id}): {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        print(f"发送弹幕时发生错误 (房间: {room_id}): {str(e)}")
        return False

def main():
    # 从配置文件加载设置
    config = load_config()
    if not config:
        return
    
    room_ids = config['room_ids']
    message = config['message']
    csrf = config['csrf']
    sessdata = config['sessdata']
    interval = config.get('interval', 20)  # 默认间隔20秒
    
    print("使用配置文件中的设置发送弹幕")
    print(f"直播间ID列表: {room_ids}")
    print(f"弹幕内容: {message}")
    print(f"发送间隔: {interval}秒")
    
    # 持续发送弹幕，每次间隔指定秒数
    print(f"开始发送弹幕，每{interval}秒发送一次，按 Ctrl+C 停止")
    try:
        while True:
            for room_id in room_ids:
                # 发送弹幕
                success = send_live_danmaku(room_id, message, csrf, sessdata)
                
                if not success:
                    print(f"弹幕发送失败，房间 {room_id} 将在下一轮重试...")
                
                # 在发送下一个房间的弹幕前稍作延迟，避免请求过于频繁
                time.sleep(1)
            
            print(f"本轮发送完成，等待{interval}秒后继续...")
            # 等待指定秒数
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n弹幕发送已停止")

if __name__ == "__main__":
    main()