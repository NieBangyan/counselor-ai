# Counselor AI

An AI-counselor system for college student consulation scenarios


The system provides AI consulting services for students through the official WeChat public account，combined with **RAG knowledge base retrieval, risk identification, asynchronous task processing, and manual takeover mechanisms**, it enables AI counselor and human counselors to work in synergy


---

## Key Features

- the office wechat AI auto reply
- Multi-turn dialogue and context management
- RAG Local Knowledge Base Search
- Multi user independent dialogue
- Redis + RQ asynchronous task handling
- Identifying risks in studens'messages 
- Automatic alerts for high-risk events
- councelor risk management workbench
- High-risk dialogue manual takeover
- counselor reply on backend to student wechat
- Cloud Server Setup
 
---

## System Process

```text
student
 │
 ▼
official WeChat
 │
 ▼
FastAPI
 │
 ▼
Redis / RQ
 │
 ├───────────────────────┐
 ▼                       ▼
Risk Identification      RAG Knowledge Retrieval
 │                       │
 ▼                       ▼
Risk Assessment          Large Language Model
 │                       │
 │                       ▼
 │                       AI reply
 │
 ▼
high risk event
 │
 ▼
Risk Alert
 │
 ▼
counselor workbench
 │
 ▼
Manual takeover
 │
 ▼
offical wechat 
 │
 ▼
student
```

---

## Multi-user conversation

The system maintains separate records for different students:

- Conversation context
- Message history
- Risk status
- Manual takeover status

A single student switching to manual intervention will not affect other students’ continued use of the AI service.

The current testing environment uses a single RQ worker, thus supporting asynchronous task queuing for multiple users; to enhance parallel processing capability, scaling can be achieved by adding more workers and server resources.

---

## Risk Identification and Manual Takeover

When the system detects high-risk information, it triggers a manual handling process：

```text
AI
 │
 ▼
risk indentify
 │
 ▼
CRISIS
 │
 ▼
HUMAN_PENDING
 │
 ▼
Counselor Access
 │
 ▼
HUMAN_ACTIVE
 │
 ▼
Manual processing
 │
 ▼
RESOLVED
```

### HUMAN_PENDING

系统已经发现风险事件，等待辅导员接入。

### HUMAN_ACTIVE

辅导员已经接管当前会话。

此时 AI 暂停该学生会话的普通自动回复，避免 AI 与辅导员同时回复。

### RESOLVED

本次风险事件处理完成。

---

## 📚 RAG 知识库

系统使用本地知识库增强 AI 的回答能力。

主要使用：

- Sentence Transformers
- Embedding
- FAISS
- RAG

知识库内容经过切分和向量化后建立 FAISS 索引，在学生提问时检索相关内容并提供给大语言模型作为回答参考。

---

## 🛠️ 技术栈

### Backend

- Python
- FastAPI
- Uvicorn

### AI / RAG

- Sentence Transformers
- Transformers
- FAISS
- 大语言模型 API

### Queue

- Redis
- RQ

### Deployment

- Ubuntu
- Nginx
- systemd
- 腾讯云 CVM

### Frontend

- HTML / CSS / JavaScript
- 辅导员风险处置工作台

---

## 项目结构

```text
counselor-ai/
├── data/               # 知识库原始数据
├── frontend/           # 辅导员前端
├── src/                # 后端核心代码
├── storage/            # FAISS 索引、知识块等
├── tests/              # 测试
├── requirements.txt    # Python 依赖
└── README.md
```

---

## 本地运行

### 1. 克隆项目

```bash
git clone https://github.com/NieBangyan/counselor-ai.git
cd counselor-ai
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows：

```powershell
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动 Redis

确保 Redis 服务已经运行。

### 5. 启动 FastAPI

```bash
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

### 6. 启动 Worker

打开另一个终端：

```bash
python -m src.run_worker
```

---

## ☁️ 部署架构

当前项目已经部署至 Ubuntu 云服务器。

```text
Internet
   │
   ▼
 Nginx
   │
   ▼
FastAPI
   │
   ├── Redis / RQ
   │
   ├── RAG / FAISS
   │
   ├── Embedding Model
   │
   └── LLM API
```

FastAPI 与 RQ Worker 作为服务器常驻服务运行，不依赖开发者本地电脑保持在线。

---

## 📌 项目定位

本项目的目标不是使用 AI 完全替代人工辅导员，而是建立：

> **AI 自动服务 + 风险识别 + 人工接管**

的人机协同模式。

AI 负责高频、即时的基础咨询服务；对于需要人工介入的高风险场景，由系统及时转交辅导员处理。

最终形成：

**学生咨询 → AI 服务 → 风险发现 → 人工介入 → 辅导员处置**

的完整服务闭环。

---

## ⚠️ 说明

本项目目前主要用于学习、测试和项目展示，并非正式投入使用的心理健康或紧急救助系统。

风险识别结果不能替代专业人员的判断，实际投入使用前还需要进一步完善安全、隐私、权限、数据保护和人工处置机制。
