# 闲鱼消息管理 CLI 工具规格

## 项目概述

- **项目名称**: xianyu-cli
- **类型**: Python CLI 工具
- **核心功能**: 闲鱼消息收发、商品管理、实时消息监听
- **目标用户**: 闲鱼卖家、自动化运营者

## 功能列表

### 1. 消息收发
- [ ] 发送消息给买家
- [ ] 接收实时消息（WebSocket）
- [ ] 查看会话列表

### 2. 商品管理
- [ ] 获取商品详情
- [ ] 发布商品（下单功能）

### 3. 用户管理
- [ ] 登录状态检查
- [ ] Cookie 管理

### 4. 实时监听
- [ ] WebSocket 实时接收消息
- [ ] 心跳维护
- [ ] 自动重连

## 技术实现

### API 层
基于 `XianyuAutoAgent` 项目的 API 封装：
- mtop 接口调用
- Token 签名机制
- Cookie 管理

### CLI 框架
使用 Click 框架构建交互式 CLI

### 目录结构
```
xianyu-cli/
├── xianyu_cli/
│   ├── __init__.py
│   ├── cli.py          # Click 入口
│   ├── api.py          # API 封装
│   ├── websocket.py    # WebSocket 客户端
│   └── utils.py        # 工具函数
├── tests/
├── setup.py
├── requirements.txt
└── .env.example
```

## 验收标准

1. CLI 工具可正常安装运行
2. 能够配置 Cookie 并验证登录
3. 能够获取商品详情
4. 能够接收实时消息
5. 代码结构清晰，注释完整