from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.counseling.counselor import Counselor
from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever
from src.routing.intent_router import IntentRouter


# ============================================================
# Global Services
# ============================================================

retriever: Retriever | None = None
deepseek_client: DeepSeekClient | None = None
intent_router: IntentRouter | None = None
counselor: Counselor | None = None


# ============================================================
# Lifespan
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever
    global deepseek_client
    global intent_router
    global counselor

    print("正在加载 AI 辅导员系统...")

    retriever = Retriever()
    deepseek_client = DeepSeekClient()
    intent_router = IntentRouter()
    counselor = Counselor()

    print("AI 辅导员系统加载完成。")

    yield

    print("AI 辅导员系统已关闭。")


# ============================================================
# FastAPI
# ============================================================


app = FastAPI(
    title="Counselor AI",
    description=(
        "集学生手册政策问答与基础心理支持"
        "于一体的 AI 辅导员服务"
    ),
    version="0.2.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1):\d+"
    ),
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
    intent: str
    answer: str

    retrieved_sources: list[Source] = Field(
        default_factory=list
    )

    cited_sources: list[Source] = Field(
        default_factory=list
    )


# ============================================================
# Helper Functions
# ============================================================


def build_sources(
    results: list[dict],
) -> list[Source]:
    """
    将 Retriever 的结果转换成 API Source。
    """
    sources: list[Source] = []

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

        sources.append(source)

    return sources


def get_cited_sources(
    retrieved_sources: list[Source],
    cited_source_ids: list[str],
) -> list[Source]:
    """
    根据 S1 / S2 等引用 ID，
    找出真正被模型引用的来源。
    """
    source_map = {
        source.source_id: source
        for source in retrieved_sources
    }

    cited_sources = [
        source_map[source_id]
        for source_id in cited_source_ids
        if source_id in source_map
    ]

    return cited_sources


# ============================================================
# Basic Routes
# ============================================================


@app.get("/")
def root():
    return {
        "name": "Counselor AI",
        "version": "0.2.0",
        "status": "running",
        "capabilities": [
            "policy",
            "counseling",
        ],
    }


@app.get("/health")
def health():
    rag_ready = (
        retriever is not None
        and deepseek_client is not None
    )

    router_ready = (
        intent_router is not None
    )

    counseling_ready = (
        counselor is not None
    )

    ready = (
        rag_ready
        and router_ready
        and counseling_ready
    )

    return {
        "status": (
            "ok"
            if ready
            else "starting"
        ),
        "system_ready": ready,
        "rag_ready": rag_ready,
        "router_ready": router_ready,
        "counseling_ready": counseling_ready,
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
        or intent_router is None
        or counselor is None
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "AI counselor system "
                "is not ready."
            ),
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail=(
                "Question cannot be empty."
            ),
        )

    try:
        # ====================================================
        # 1. Intent Routing
        # ====================================================

        intent = intent_router.classify(
            question
        )

        # 临时保留，方便确认前端实际走了哪个分支。
        print(
            f"[ROUTER] {question} -> {intent}"
        )

        # ====================================================
        # 2. Counseling
        # ====================================================

        if intent == "counseling":
            answer = counselor.answer(
                question
            )

            return ChatResponse(
                intent="counseling",
                answer=answer,
                retrieved_sources=[],
                cited_sources=[],
            )

        # ====================================================
        # 3. Other
        # ====================================================

        if intent == "other":
            return ChatResponse(
                intent="other",
                answer=(
                    "这个问题目前不属于我可以处理的"
                    "学生政策问答或基础心理支持范围。"
                    "\n\n"
                    "你可以询问学生手册相关规定，"
                    "例如请假、学籍、选课、成绩、"
                    "奖学金、毕业等问题；"
                    "也可以和我聊聊学习压力、情绪、"
                    "焦虑、人际关系等困扰。"
                ),
                retrieved_sources=[],
                cited_sources=[],
            )

        # ====================================================
        # 4. Policy RAG
        # ====================================================

        results = retriever.retrieve(
            question
        )

        llm_result = (
            deepseek_client.answer(
                question=question,
                retrieval_results=results,
            )
        )

        answer = llm_result["answer"]

        cited_source_ids = (
            llm_result.get(
                "cited_source_ids",
                [],
            )
        )

        retrieved_sources = (
            build_sources(
                results
            )
        )

        cited_sources = (
            get_cited_sources(
                retrieved_sources=(
                    retrieved_sources
                ),
                cited_source_ids=(
                    cited_source_ids
                ),
            )
        )

        return ChatResponse(
            intent="policy",
            answer=answer,
            retrieved_sources=(
                retrieved_sources
            ),
            cited_sources=(
                cited_sources
            ),
        )

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"/chat 处理失败："
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "处理问题时发生内部错误，"
                "请稍后重试。"
            ),
        ) from exc