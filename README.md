# Counselor AI

An AI-powered counselor assistant for university students.

## Current Progress

-  Extract text from the student handbook PDF
-  Build a structured knowledge base
-  Semantic retrieval
-  RAG-based question answering
-  WeChat Official Account integration
```
学生
 ↓
微信公众号
 ↓
腾讯云 Nginx
 ↓
FastAPI
 ↓
Redis + RQ
 ↓
AI 辅导员服务
 ├─ 意图识别
 ├─ 风险检测
 ├─ RAG 知识库
 └─ 大语言模型

高风险
 ↓
Alert Service
 ↓
Handoff Service
 ↓
辅导员工作台
 ↓
微信客服消息
 ↓
学生
```