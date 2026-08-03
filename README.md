# B站直播弹幕发送工具

一个简单的Python脚本，用于向B站直播间自动发送弹幕。

## 功能

- 自动向指定直播间发送弹幕
- 支持自定义弹幕内容
- 支持多个直播间批量发送（自动过滤无效房间 ID）
- 支持自定义发送间隔，并带随机抖动以降低风控风险
- 自动检测登录态失效并停机提示
- 复用 TCP 连接（`requests.Session`）提升发送稳定性
- 敏感凭据支持环境变量，避免写入配置文件
- 通过 `logging` 输出带时间戳的日志
- 简单易用，无需复杂配置
- （后续会考虑多账号配置，其余平台如抖音快手虎牙斗鱼等发送弹幕的直播视频平台，以及GUI界面）

## 使用方法

1. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

2. 准备配置文件：
   - 复制模板 `config.example.json` 为 `config.json`
   - 修改 `config.json` 中的配置参数：

   | 字段 | 说明 |
   | --- | --- |
   | `room_ids` | 直播间ID列表（正整数，支持多个）；`0`/无效值会被自动忽略 |
   | `message` | 要发送的弹幕内容（不能为空） |
   | `csrf` | B站账户的 `bili_jct` 值（也可用环境变量 `BILI_CSRF`） |
   | `sessdata` | B站账户的 `SESSDATA` 值（也可用环境变量 `BILI_SESSDATA`） |
   | `interval` | 基础发送间隔（秒），默认 20 |
   | `jitter` | 随机抖动范围（秒），实际间隔为 `interval ± jitter`，默认 5 |

   > 房间 ID 取自直播间地址：`https://live.bilibili.com/xxxxxxxx` 中的 `xxxxxxxx`。

3. 运行脚本:
   ```
   python bili_danmu.py
   ```
   也可指定配置文件路径：
   ```
   python bili_danmu.py -c /path/to/your/config.json
   ```

4. （可选）使用环境变量传入敏感凭据，避免把 Cookie 写进 `config.json`：
   ```
   set BILI_CSRF=你的bili_jct
   set BILI_SESSDATA=你的SESSDATA
   python send_live_danmaku.py
   ```
   （环境变量优先级高于 `config.json` 中的值）

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
仓库已通过 `.gitignore` 忽略 `config.json`，请勿手动将其提交到公开仓库。

## 依赖组件

- requests>=2.31.0

## 注意事项

- 使用前需要获取有效的B站Cookie信息（bili_jct和SESSDATA）
- 请遵守B站使用规则，避免频繁发送弹幕
- 本工具仅供学习交流使用，请勿用于非法用途
- 有问题给我反馈谢谢大家
