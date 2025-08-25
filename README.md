# MSPRO 财务管理系统

## 简介
MSPRO 财务管理系统是一个基于 Flask 开发的 Web 应用，旨在为公寓或酒店管理者提供一个清晰、直观的预订与财务数据分析平台。系统支持多用户权限管理，能够展示详细的收入、支出、入住率等核心指标，并能一键生成专业的月度财务报表。

核心数据通过本地 Excel 文件进行维护，并通过命令行工具一键同步至线上生产数据库，确保数据管理的灵活性与安全性。

---

## 功能模块
- **数据看板 (Dashboard)**: 动态展示年度、月度的总收入、总支出、毛利润、管理费和净收入等关键财务指标。
- **图表分析**: 提供多维度图表，包括：
  - 年度月度收入/支出对比
  - 与前一年度的收入对比
  - 各预订渠道收入来源分布饼图
- **详细数据表格**: 集中展示所有预订（Booking）和支出（Expense）的详细记录，支持编辑和删除。
- **月结单生成**: 根据筛选的年份、月份和房源，一键生成详细的 PDF 格式月度财务报表。
- **用户权限管理 (管理员)**:
  - 管理员 (`admin`) 可以查看所有数据。
  - 业主 (`owner`) 只能查看分配给其名下的房源数据。
  - 管理员可以为业主账户分配房源权限及修改管理费率。
- **安全的用户认证**: 包括用户登录、登出、修改密码，以及由管理员生成密码重置链接。
- **数据导入**: 通过命令行工具 `flask import-data` 将本地 `excel_data/` 目录下的 Excel 文件数据批量导入生产数据库。

---

## 技术栈
- **后端**: Python, Flask
- **数据库**: PostgreSQL (生产环境), SQLite (开发环境)
- **ORM**: Flask-SQLAlchemy, Flask-Migrate
- **前端**: HTML, CSS, JavaScript, Chart.js
- **认证**: Flask-Login, Flask-WTF
- **部署**: Docker, Gunicorn, Whitenoise
- **数据处理**: Pandas, openpyxl
- **PDF 生成**: pdfkit, wkhtmltopdf

---

## 安装与运行 (本地开发)

1.  **克隆仓库**
    ```bash
    git clone <repository-url>
    cd msprodata_render
    ```

2.  **创建并激活虚拟环境**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置环境变量**
    在项目根目录创建 `.env` 文件，并设置以下变量。本地开发时，可使用默认的 SQLite 数据库。
    ```env
    # .env
    SECRET_KEY='a_secure_random_string'
    # DATABASE_URL='postgresql://user:password@host:port/dbname' # (可选) 生产环境URL
    ```

5.  **初始化数据库**
    ```bash
    flask db init  # 仅在首次设置时运行
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

6.  **创建第一个用户**
    通过 `flask shell` 手动创建第一个管理员用户。
    ```python
    from mspro_app import create_app, db
    from mspro_app.models import User
    app = create_app()
    with app.app_context():
        user = User(id='admin', role='admin')
        user.set_password('your_secure_password')
        db.session.add(user)
        db.session.commit()
    ```

7.  **运行应用**
    ```bash
    flask run
    ```
    访问 `http://127.0.0.1:5000` 查看应用。

---

## 数据管理

本项目最核心的工作流程是**从本地 Excel 更新数据到生产数据库**。

1.  **数据源**: 所有预订和支出数据都存储在项目根目录下的 `excel_data/` 文件夹中的 Excel 文件里。此文件夹已加入 `.gitignore`，不会被上传到代码仓库。

2.  **操作命令**: 在本地电脑上运行 `flask import-data` 命令。

3.  **工作机制**:
    - 该命令会读取 `.env` 文件中的 `DATABASE_URL`，直接连接到 **Render 上的生产数据库**。
    - 连接成功后，它会**清空** `Booking` 和 `Expense` 两张表中的所有现有数据。
    - 接着，它会读取 `excel_data/` 目录下的所有 Excel 文件，并将新数据导入数据库。
    - 此操作**不会**影响 `User` 表，所有用户账户和密码都是安全的。

---

## 部署 (Render.com)

本项目已配置为通过 Docker 在 Render 平台上进行部署。

-   `Dockerfile`: 定义了构建镜像所需的所有步骤，包括安装系统依赖（如 `wkhtmltopdf` 和中文字体）、Python 库以及复制项目文件。
-   `start.sh`: 作为容器的启动命令。它首先执行 `flask db upgrade` 来确保数据库结构是最新状态，然后使用 Gunicorn 启动 Web 服务器。

每次将代码推送到关联的 GitHub 仓库时，Render 都会自动触发新的构建和部署。

---

## 开发规范
- **禁止硬编码**: 敏感信息（如 `SECRET_KEY`, `DATABASE_URL`）必须通过环境变量配置。
- **数据库迁移**: 对 `models.py` 的任何修改都必须生成一个新的迁移脚本 (`flask db migrate`) 并提交到代码仓库。
- **数据安全**: `flask import-data` 是一个高风险操作。在执行前，务必确认本地 Excel 数据的准确性。
- **代码风格**: 遵循 PEP 8 编码规范。
