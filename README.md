# Talk to Data - 对话式数据分析工具

![Electron-Python Data Analysis](https://img.shields.io/badge/Electron-Python-blue)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](LICENSE)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/WALKERKILLER/Talk-to-Data)
![](https://dl3.img.timecdn.cn/2025/07/01/ICON.png!h.webp)
一个基于Electron和Python的桌面应用，通过自然语言指令实现智能数据分析。
![](https://dl3.img.timecdn.cn/2025/06/29/PREVIEW.png)
![](https://dl.img.timecdn.cn/2025/06/29/EXAMPLE.png)
## ✨ 功能特性

- **自然语言交互** - 用日常语言描述分析需求
- **数据可视化** - 自动生成专业图表
- **实时反馈** - 流式显示分析过程
- **报告导出** - 一键生成Markdown格式分析报告
- **多会话管理** - 隔离不同分析任务
- **性能评估** - 生成分析质量评分图表

## 🚧 未来计划

- [x] 支持更多文件格式(XLSX, JSON,SHP等)和多文件上传(已经支持)
- [ ] 集成更丰富的外部工具和推理工具
- [ ] 扩展支持更多模型供应商(目前已支持OPENAI格式的供应商)
- [x] 新增对话记录与连续对话功能(已经支持)
- [ ] 增强可视化图表交互能力
- [ ] 支持自定义分析模板

## 🛠 技术栈

| 组件        | 技术选型                  |
|-------------|--------------------------|
| 前端框架    | Electron + HTML/CSS/JS   |
| 后端服务    | Python Flask             |
| 数据处理    | pandas + NumPy           |
| 可视化      | Matplotlib/Plotly        |
| AI集成      | OpenAI兼容API            |
| 构建工具    | PyInstaller + Electron Builder |

## 📦 安装指南

### 开发环境运行

1. 确保已安装:
   - Node.js v16+
   - Python 3.8+
   - Git

2. 克隆仓库:
```bash
git clone https://github.com/WALKERKILLER/Talk-to-Data.git
cd Talk-to-Data-Main
```

3. 安装依赖:
```bash
npm install
pip install -r requirements.txt
```

4. 启动应用:
```bash
npm start
```

### 生产环境构建

```bash
# 构建Python后端
npm run build:python

# 构建Electron应用
npm run build:electron

# 完整打包(生成安装包)
npm run package
```

## 🚀 使用教程

1. **设置API连接**
   - 在侧边栏输入API地址和密钥
   - 点击"测试连接"验证配置

2. **上传数据文件**
   - 拖拽或选择CSV,XLSX,SHP,JSON文件
   - 系统自动解析数据结构

3. **输入分析任务**
   ```示例
   "统计主导变量的热度"
   "计算每月平均增长率"
   "找出异常值并可视化"
   ```

4. **查看分析过程**
   - 实时显示分析步骤
   - 自动生成可视化图表

5. **导出报告**
   - 点击"导出Markdown"保存完整分析

## 📂 项目结构

```
talk-to-data/
├── app.py                # Flask主应用
├── talk_to_data_core.py  # 数据分析核心逻辑
├── tools.py              # 工具函数与扩展
├── evaluator.py          # 分析评估与评分
├── main.js               # Electron主进程
├── package.json          # 项目配置
├── preload.js            # Electron预处理脚本
├── static/               # 静态资源
│   ├── script.js         # 前端逻辑
│   └── style.css         # 样式表
├── templates/            # HTML模板
│   └── index.html        # 主界面
└── py-backend.spec       # PyInstaller配置
```

## 🤝 贡献指南

欢迎提交Pull Request！请确保:

1. 兼容现有代码
2. 添加适当的单元测试
3. 更新相关文档

## 📄 许可证

本项目采用 [ISC License](LICENSE)
