from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever


retriever: Retriever | None = None
deepseek_client: DeepSeekClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever, deepseek_client

    print("正在加载 RAG 系统...")

    retriever = Retriever()
    deepseek_client = DeepSeekClient()

    print("RAG 系统加载完成。")

    yield


app = FastAPI(
    title="Counselor AI",
    description="基于学生手册知识库的辅导员 AI 问答服务",
    version="0.1.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="学生提出的问题",
    )


class Source(BaseModel):
    document_title: str | None = None
    chapter: str | None = None
    article: str | None = None
    pdf_pages: list[int] = []
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/")
def root():
    return {
        "name": "Counselor AI",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):
    if retriever is None or deepseek_client is None:
        raise HTTPException(
            status_code=503,
            detail="RAG system is not ready.",
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    try:
        results = retriever.retrieve(question)

        answer = deepseek_client.answer(
            question=question,
            retrieval_results=results,
        )

        sources = [
            Source(
                document_title=item.get("document_title"),
                chapter=item.get("chapter"),
                article=item.get("article"),
                pdf_pages=item.get("pdf_pages", []),
                score=item["score"],
            )
            for item in results
        ]

        return ChatResponse(
            answer=answer,
            sources=sources,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc