# GitHub 上传指南

## 📤 上传到 GitHub 的步骤

### 1. 初始化 Git 仓库

```bash
cd "C:\Language change project"
git init
```

### 2. 添加文件到 Git

```bash
git add .
```

### 3. 提交到本地仓库

```bash
git commit -m "Initial commit: 一键翻译助手"
```

### 4. 在 GitHub 创建新仓库

1. 访问 https://github.com/new
2. 填写仓库名称（例如：`translation-tool`）
3. 选择 Public（公开）或 Private（私有）
4. **不要**勾选 "Add a README file"
5. 点击 "Create repository"

### 5. 关联远程仓库

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
```

### 6. 推送到 GitHub

```bash
git push -u origin main
```

---

## ⚠️ 重要提醒

### 已处理的敏感信息

✅ **config.json** - 已替换为 ×××××  
✅ **config.example.json** - 创建了示例配置  
✅ **.gitignore** - 已配置忽略敏感文件  

### 上传前检查清单

- [ ] 确认 `config.json` 中的 API 密钥已替换为 ××××
- [ ] 检查 `.gitignore` 文件是否正确配置
- [ ] 确认没有其他敏感信息（如个人信息、路径等）

---

## 📋 项目文件说明

### 需要上传的文件：
- ✅ `translator.py` - 翻译核心代码
- ✅ `hotkey_listener.py` - 快捷键监听程序
- ✅ `requirements.txt` - 依赖包列表
- ✅ `config.example.json` - 配置文件示例
- ✅ `README_GITHUB.md` - GitHub 主说明文档
- ✅ `LICENSE` - MIT 许可证
- ✅ `.gitignore` - Git 忽略规则
- ✅ `启动翻译助手.bat` - Windows 启动脚本

### 不会上传的文件（已在 .gitignore 中）：
- ❌ `config.json` - 包含真实 API 密钥（已被 .gitignore 忽略）
- ❌ `__pycache__/` - Python 缓存文件

---

## 📝 上传后的操作

### 1. 重命名主 README

上传后，将 `README_GITHUB.md` 重命名为 `README.md`：

```bash
git mv README_GITHUB.md README.md
git mv README.md README_LOCAL.md
git commit -m "Update README for GitHub"
git push
```

### 2. 添加 Topics

在 GitHub 仓库页面右侧点击"⚙️ 设置"，添加标签：
- `python`
- `translation`
- `windows`
- `baidu-translate`
- `hotkey`

### 3. 配置仓库描述

在仓库顶部添加描述：
```
一键翻译助手 - 基于百度翻译API的Windows桌面快捷翻译工具
```

---

## 🔒 保护你的本地密钥

上传后，如需恢复本地的真实配置：

1. 创建 `config.local.json` 存放真实密钥
2. 在 `.gitignore` 中添加 `config.local.json`
3. 修改代码读取 `config.local.json`（如果存在）

---

## 💡 其他人如何使用

1. Clone 仓库
2. 复制 `config.example.json` 为 `config.json`
3. 填入自己的百度翻译 API 密钥
4. 安装依赖并运行

---

**准备好后就可以上传了！** 🚀
