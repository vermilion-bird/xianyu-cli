# xianyu-cli

闲鱼 CLI 工具 🐟

基于 [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent) 项目的 API 实现。

## 安装

```bash
pip install -r requirements.txt
pip install -e . --break-system-packages
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 设置你的 Cookie：

```bash
# 方式一: 命令行设置
xianyu config set-cookies "your_cookie_string"

# 方式二: 直接编辑 .env 文件
```

获取 Cookie: 打开闲鱼网页版 → F12 → Network → 点击任意请求 → 复制 Request Headers 中的 Cookie

## 使用

### 检查登录状态
```bash
xianyu login
```

### 获取商品详情
```bash
xianyu item <商品ID>
```

### 监听实时消息
```bash
xianyu listen
xianyu listen --verbose   # 显示详细日志
```

收到消息时会输出：
```
----------------------------------------
📩 新消息!
  👤 用户: 买家昵称
  🆔 ID: 495429891
  🔗 Chat ID: 123456789
  📦 商品: 804468032355
  💬 内容: 消息内容
----------------------------------------
```

### 发送消息
```bash
xianyu send <chat_id> <to_user_id> "<消息内容>"
```

`chat_id` 从 `listen` 输出的 `🔗 Chat ID` 获取：
```bash
xianyu send 123456789 495429891 "好的，没问题"
```

### 配置管理
```bash
xianyu config show      # 显示当前配置
xianyu config set-cookies <cookies>  # 设置 Cookie
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `login` | 检查登录状态 |
| `item <id>` | 获取商品详情 |
| `listen` | 监听实时消息（显示 Chat ID） |
| `listen --verbose` | 监听实时消息（显示详细日志） |
| `send <chat_id> <user_id> <msg>` | 发送消息 |
| `config show` | 显示配置 |
| `config set-cookies` | 设置 Cookie |

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt --break-system-packages

# 本地安装（editable 模式，改完代码直接生效）
pip install -e . --break-system-packages

# 运行
xianyu --help
```

## 相关项目

- [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent) - 智能闲鱼客服机器人