# iHome PMS - 智能民宿管理系统 v3.0

基于 PyQt5 + MySQL 的桌面端民宿管理软件，支持多人协作、角色权限、智能推荐与数据可视化。

## 功能模块

| 模块 | 描述 |
|------|------|
| 仪表盘 | 千人千面智能工作台（管理员/前台/财务/客房四种视角） |
| 房态管理 | 10间客房状态管理（空闲/已入住/已预订/脏房/维修） |
| 预订管理 | 订单创建、确认、取消、房型选择 |
| 入住办理 | 四步向导流程（订单确认→证件登记→选房分配→账务确认） |
| 退房结算 | 退房结账、杂费添加、会员积分更新 |
| 收银台 | 账务管理、退款处理 |
| 客户管理 | 客户档案、VIP 等级、偏好记录 |
| 报表中心 | 经营报表 + 智能分析洞察 |
| 系统设置 | 用户管理、操作日志、夜审 |

## 技术栈

- **UI**: PyQt5 + QSS（Frameless 窗口、自定义标题栏）
- **ORM**: SQLAlchemy 2.0
- **数据库**: MySQL 8.0
- **测试**: pytest（39 条测试用例，10 个测试文件）
- **架构**: View → Service → Model 三层分离 + EventBus 跨页面同步

## 项目结构

```
v3.0/
├── main.py                     # 应用入口
├── src/
│   ├── config.py               # 数据库与系统配置
│   ├── models/                 # 数据模型（User, Room, Order, Customer, BillItem 等）
│   ├── services/               # 业务服务层
│   │   ├── pms_service.py      # 核心业务逻辑（入住/退房/订单/房态/账务）
│   │   ├── dashboard_service.py # 智能工作台数据聚合
│   │   ├── smart_service.py    # 客情推荐与行动队列
│   │   ├── audit_service.py    # 操作日志与夜审
│   │   └── report_insight_service.py # 报表智能分析
│   ├── views/                  # UI 视图层
│   ├── utils/
│   │   ├── db.py               # 数据库初始化、演示数据
│   │   └── event_bus.py        # 跨页面事件总线
│   └── resources/
│       └── theme.py            # 全局主题配置
└── tests/                      # 单元测试（39 条）
```

## 快速开始

### 环境要求

- Python 3.9+
- MySQL 8.0+

### 安装

```bash
pip install PyQt5 SQLAlchemy pymysql
```

### 配置数据库

编辑 `src/config.py`，修改数据库连接信息：

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "你的密码",
    "database": "homestay_pms",
    "charset": "utf8mb4",
}
```

### 运行

```bash
python main.py
```

首次运行会自动创建数据库、表结构和演示数据。

### 测试

```bash
pytest tests/ -v
```

## 演示账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| front | front123 | 前台 |
| finance | finance123 | 财务 |
| room | room123 | 客房 |

## 许可

课程项目，仅供学习参考。
