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

2. 准备配置文件（可选，可跳过）：
   - 不手动创建也行：直接运行脚本，若 `config.json` 不存在会**自动生成默认模板**，
     并提示你粘贴 Cookie 以填充凭据（见第 4 步）。
   - 也可以手动准备：复制模板 `config.example.json` 为 `config.json`，
     修改其中的配置参数：

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

4. 凭据自动获取（运行时交互）：
   当 `config.json` 中的 `csrf` / `sessdata` 仍为空或保留默认占位符时，
   运行脚本会自动提示你粘贴浏览器整段 Cookie，程序解析出 `bili_jct` 和 `SESSDATA`
   后自动写回 `config.json`（其余配置不动），随后继续发送弹幕。例如：
   ```
   未检测到有效的 csrf / sessdata。
   请粘贴浏览器复制的整段 Cookie（形如 SESSDATA=xxx; bili_jct=yyy; ...）：
   Cookie> <在此粘贴整段 Cookie>
   ```
   > 程序会自动对 `SESSDATA` 做 URL 解码（`%2C`→`,` 等），无需手动处理。
   > 凭据已写入配置后，再次运行不会再提示。

5. （可选）使用环境变量传入敏感凭据，避免把 Cookie 写进 `config.json`：
   ```
   set BILI_CSRF=你的bili_jct
   set BILI_SESSDATA=你的SESSDATA
   python bili_danmu.py
   ```
   （环境变量优先级高于 `config.json` 中的值）

## 如何获取B站Cookie信息

要使用此工具，您需要获取B站账户的Cookie信息，包括`bili_jct`和`SESSDATA`：

1. 打开浏览器并登录您的B站账户
2. 进入任意B站直播间，按F12打开开发者工具
3. 在开发者工具中找到"Application"（应用程序）或"Storage"（存储）选项卡
4. 在左侧的"Storage" 部分找到"Cookies"，然后点击 `https://live.bilibili.com`
5. 复制整段 Cookie（包含 `SESSDATA`、`bili_jct` 等所有字段），在脚本提示时直接粘贴即可；
   或仅复制以下两个值手动填入 `config.json`：
   - `bili_jct` 对应配置文件中的 `csrf`
   - `SESSDATA` 对应配置文件中的 `sessdata`

注意：这些Cookie值是您账户的敏感信息，请妥善保管，不要泄露给他人。
仓库已通过 `.gitignore` 忽略 `config.json`，请勿手动将其提交到公开仓库。
`SESSDATA` 为登录态，过期后将 `config.json` 中的凭据改回占位符（或清空），重新运行脚本按提示粘贴 Cookie 更新即可。

## 依赖组件

- requests>=2.31.0

## 注意事项

- 使用前需要获取有效的B站Cookie信息（bili_jct和SESSDATA）
- 请遵守B站使用规则，避免频繁发送弹幕
- 本工具仅供学习交流使用，请勿用于非法用途
- 有问题给我反馈谢谢大家
