# Backend (Flask)

## 启动

在 PowerShell 里运行：

```powershell
cd backend
.\start.ps1
```

服务默认监听 `http://localhost:5000`。

## 主要接口

- `GET /api/public/site`：站点配置（公司介绍、联系方式、首页图/视频 URL）
- `GET /api/public/products`：产品列表
- `POST /api/public/leads`：保存前端提交的联系方式

- `GET /api/admin/site` / `PUT /api/admin/site`：管理端读取/保存站点配置
- `GET /api/admin/products` / `POST /api/admin/products` / `DELETE /api/admin/products/:id`：管理端维护产品
- `POST /api/admin/upload`：上传图片/视频（返回可访问的 URL）
- `GET /media/<filename>`：静态媒体访问

## 数据位置

SQLite 数据库与上传文件存放在 `backend/data/`。

