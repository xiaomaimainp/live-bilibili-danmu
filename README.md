# B站直播弹幕发送工具

一个简单的Python脚本，用于向B站直播间自动发送弹幕。

## 功能

- 自动向指定直播间发送弹幕
- 支持自定义弹幕内容
- 支持多个直播间批量发送
- 支持自定义发送间隔
- 简单易用，无需复杂配置
 （后续会考虑多账号配置，其余平台如抖音快手虎牙斗鱼等发送弹幕的直播视频平台）
## 使用方法

1. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

2. 修改 [config.json] ./config.json) 文件中的配置参数:  
   - `room_ids`: 直播间ID列表，支持多个直播间就是           
   - https://live.bilibili.com/yyyyyyyy 和 https://live.bilibili.com/xxxxxxxx 
   - 比如"room_ids": [yyyyyyyy,xxxxxxxx] 直播间ID之间用逗号隔开
   - `message`: 要发送的弹幕内容
   - `csrf`: B站账户的bili_jct值
   - `sessdata`: B站账户的SESSDATA值
   - `interval`: 发送间隔（秒），默认为20秒

1. 运行脚本:
   ```
   python send_live_danmu.py
   ```

## 如何获取B站Cookie信息

要使用此工具，您需要获取B站账户的Cookie信息，包括`bili_jct`和`SESSDATA`：

1. 打开浏览器并登录您的B站账户
2. 进入任意B站页面，按F12打开开发者工具
3. 在开发者工具中找到"Application"（应用程序）或"Storage"（存储）选项卡
4. 在左侧的"Storage"部分找到"Cookies"，然后点击`https://www.bilibili.com`
5. 在右侧的Cookie列表中找到以下两个值并复制：
   - `bili_jct` 对应配置文件中的 `csrf`
   - `SESSDATA` 对应配置文件中的 `sessdata`

注意：这些Cookie值是您账户的敏感信息，请妥善保管，不要泄露给他人。

## 依赖组件

- requests>=2.31.0

## 注意事项

- 使用前需要获取有效的B站Cookie信息（bili_jct和SESSDATA）
- 请遵守B站使用规则，避免频繁发送弹幕
- 本工具仅供学习交流使用，请勿用于非法用途
- 有问题给我反馈谢谢大家
