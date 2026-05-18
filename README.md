# 闲置好物 - 二手商品交易平台

## 项目介绍

闲置好物是一个功能完善的在线二手商品交易平台，采用 Flask 框架开发，前端使用 Bootstrap 5 构建响应式界面。

**核心理念**：让闲置物品焕发新价值，推动资源循环利用，构建环保可持续的交易社区。
**核心原则**：真实个人卖家，拒绝商家伪装。平台致力于打造一个纯个人交易的二手市场，让每一笔交易都建立在信任与真诚的基础上。

我们相信每一件闲置物品都有它的价值。通过平台，买家可以低价获取所需，卖家可以变现闲置物品，实现双赢。同时减少资源浪费，为环保事业贡献一份力量。

> **在线体验**：
> 
> 网址：https://xfxuezhang.cn/web/secondhand/
> 
> 用户：user001 / 123

<p align="center"><img src="https://github.com/user-attachments/assets/a0a5aea9-c119-4fcf-a6c1-c78bd714f18e" alt="image" width="1024"/></p>

<p align="center"><img src="https://github.com/user-attachments/assets/b6fff9ca-da3f-495f-a55e-fe17aa98e3e3" alt="image" width="1024"/></p>


## 功能特性

### 👤 用户模块
- **用户注册与登录**：支持用户名和邮箱注册，安全的密码存储（PBKDF2 哈希）
- **个人资料管理**：支持修改昵称、头像、个人简介、性别、地区等信息
- **学生身份认证**：提供学生认证功能，需填写学校、入学年份、毕业年份等信息
- **收藏功能**：用户可以收藏感兴趣的商品，方便后续查看

### 🛒 商品模块
- **商品发布**：支持多图上传（最多9张），包含商品名称、价格、描述、分类等信息
- **商品浏览**：支持分类筛选和关键词搜索，快速找到目标商品
- **商品详情**：展示商品图片、价格、卖家信息、发布时间等完整内容
- **商品编辑与删除**：发布者可以修改或下架自己的商品
- **商品举报**：用户可以举报违规或虚假商品，管理员审核处理
- **商品审核**：新发布的商品需要管理员审核，支持待审核/已通过/已拒绝三种状态

### 💬 消息模块
- **站内信**：买家与卖家之间可以发送私信进行沟通
- **系统通知**：商品审核结果、举报处理结果等会通过系统通知告知用户
- **一键清空**：用户可以一键清空所有通知记录
- **评论系统**：用户可以对商品发表评论，支持回复功能

### ⚙️ 管理后台
- **用户管理**：查看所有用户信息，禁用/启用用户账号
- **身份审核**：审核用户提交的学生认证申请
- **商品管理**：审核商品、查看商品列表、处理商品举报
- **公告管理**：发布和编辑平台公告
- **系统设置**：配置平台名称、公告内容等

## 技术栈

- **后端框架**: Flask (Python Web 框架)
- **前端框架**: Bootstrap 5.1.3 (响应式 CSS 框架)
- **图标库**: Font Awesome 6.4.0
- **数据存储**: JSON 文件（轻量级，无需数据库配置）
- **图片处理**: Pillow (Python PIL)
- **密码安全**: Werkzeug Security (PBKDF2 + SHA256)

## 项目结构

```
secondhand-platform/
├── app.py                 # Flask 主应用，包含所有路由和业务逻辑
├── README.md              # 项目说明文档
├── requirements.txt       # Python 依赖包列表
├── data/                  # JSON 数据存储目录
│   ├── users.json         # 用户数据
│   ├── products. json        # 商品数据
│   ├── comments. json        # 评论数据
│   ├── messages.json      # 站内信数据
│   ├── notifications.json # 通知数据
│   ├── notices. json       # 公告数据
│   ├── reports.json       # 举报数据
│   └── settings.json      # 系统设置
├── templates/             # Jinja2 模板文件
│   ├── base. html          # 基础模板（导航栏、页脚等）
│   ├── index. html         # 首页（商品列表）
│   ├── login. html         # 登录页面
│   ├── register.html      # 注册页面
│   ├── product_detail.html # 商品详情页
│   ├── product_create.html # 发布商品页
│   ├── dashboard.html     # 个人中心
│   ├── user_profile.html  # 用户资料页
│   ├── profile_edit.html  # 资料编辑页
│   ├── student_verify.html # 学生认证页
│   ├── messages.html      # 站内信列表
│   ├── message_send.html  # 发送站内信
│   ├── message_detail.html #站内信详情
│   ├── notifications.html # 通知列表
│   ├── notices.html       # 公告列表
│   ├── notice_detail.html # 公告详情
│   └── admin/             # 管理后台模板
└── static/                # 静态资源目录
```

## 环境要求

- Python 3.8 或更高版本
- 支持的操作系统：Windows、Linux、macOS

## 快速开始

### 1. 克隆或下载项目
将项目文件下载到本地目录。

### 2. 安装依赖
```bash
cd secondhand-platform
pip install -r requirements.txt
```

### 3. 启动服务
项目默认使用端口 **5000**
```bash
python start.py
```
服务启动后，访问 http://127.0.0.1:5/000

### 4. 登录管理后台
- 访问：http://127.0.0.1:5/000/admin
- 默认管理员账号：admin / admin

## 主要页面路由

| 页面 | 路由 | 说明 |
|------|------|------|
| 首页 | / | 展示所有待交易商品 |
| 登录 | /login | 用户登录入口 |
| 注册 | /register | 新用户注册 |
| 商品详情 | /product/<商品ID> | 查看商品详细信息 |
| 发布商品 | /product/create | 发布新商品 |
| 个人中心 | /dashboard | 用户中心 |
| 管理后台 | /admin | 管理员入口 |
| 用户管理 | /admin/users | 管理所有用户 |
| 商品审核 | /admin/products | 审核商品 |
| 身份审核 | /admin/verifications | 审核学生认证 |

## 数据说明

所有数据以 JSON 格式存储在 data/ 目录下：
- users.json、products.json、comments.json、messages.json、notifications.json、notices.json、reports.json、settings.json

## 安全注意事项

1. **密码存储**：用户密码使用 Werkzeug 的 generate_password_hash 加密存储
2. **Session 安全**：使用随机生成的 secret_key
3. **文件上传**：限制上传文件类型和大小
4. **权限控制**：管理后台需要 admin 角色权限

## 扩展开发

如需对接数据库，可将 app.py 中的 load_json 和 save_json 函数替换为数据库操作代码。

## 许可证

Apache 2.0 License - 可免费商用，欢迎二次开发。
