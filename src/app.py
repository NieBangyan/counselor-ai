from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

    print("RAG 系统已关闭。")


app = FastAPI(
    title="Counselor AI",
    description="基于学生手册知识库的辅导员 AI 问答服务",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request / Response Models
# ============================================================


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="学生提出的问题",
    )


class Source(BaseModel):
    source_id: str

    document_title: str | None = None
    chapter: str | None = None
    article: str | None = None

    pdf_pages: list[int] = Field(
        default_factory=list
    )

    score: float


class ChatResponse(BaseModel):
    answer: str

    retrieved_sources: list[Source] = Field(
        default_factory=list
    )

    cited_sources: list[Source] = Field(
        default_factory=list
    )


# ============================================================
# Basic Routes
# ============================================================


@app.get("/")
def root():
    return {
        "name": "Counselor AI",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    ready = (
        retriever is not None
        and deepseek_client is not None
    )

    return {
        "status": "ok" if ready else "starting",
        "rag_ready": ready,
    }


# ============================================================
# Chat
# ============================================================


@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
    if (
        retriever is None
        or deepseek_client is None
    ):
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
        # ----------------------------------------------------
        # Retrieval
        # ----------------------------------------------------

        results = retriever.retrieve(
            question
        )

        # ----------------------------------------------------
        # LLM
        # ----------------------------------------------------

        llm_result = deepseek_client.answer(
            question=question,
            retrieval_results=results,
        )

        answer = llm_result["answer"]

        cited_source_ids = llm_result.get(
            "cited_source_ids",
            [],
        )

        # ----------------------------------------------------
        # Build source objects
        # ----------------------------------------------------

        retrieved_sources: list[Source] = []

        for index, item in enumerate(
            results,
            start=1,
        ):
            source = Source(
                source_id=f"S{index}",
                document_title=item.get(
                    "document_title"
                ),
                chapter=item.get(
                    "chapter"
                ),
                article=item.get(
                    "article"
                ),
                pdf_pages=item.get(
                    "pdf_pages",
                    [],
                ),
                score=float(
                    item.get(
                        "score",
                        0.0,
                    )
                ),
            )

            retrieved_sources.append(
                source
            )

        # ----------------------------------------------------
        # Only sources actually cited by the LLM
        # ----------------------------------------------------

        source_map = {
            source.source_id: source
            for source in retrieved_sources
        }

        cited_sources = [
            source_map[source_id]
            for source_id in cited_source_ids
            if source_id in source_map
        ]

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return ChatResponse(
            answer=answer,
            retrieved_sources=(
                retrieved_sources
            ),
            cited_sources=cited_sources,
        )

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"/chat 处理失败："
            f"{type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "处理问题时发生内部错误，"
                "请稍后重试。"
            ),
        ) from exc