from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.admin.router import (
    router as admin_router,
)
from src.services.assistant_service import (
    AssistantService,
)
from src.wechat.router import (
    router as wechat_router,
)


# ============================================================
# Lifespan
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在加载 AI 辅导员系统...")

    assistant_service = (
        AssistantService()
    )

    app.state.assistant_service = (
        assistant_service
    )

    print("AI 辅导员系统加载完成。")

    # ========================================================
    # Route Debug
    # ========================================================

    print("=" * 70)
    print("当前 FastAPI 已注册路由：")

    for route in app.routes:
        path = getattr(
            route,
            "path",
            None,
        )

        methods = getattr(
            route,
            "methods",
            None,
        )

        if path:
            print(
                f"{methods} -> {path}"
            )

    print("=" * 70)

    yield

    print("AI 辅导员系统已关闭。")


# ============================================================
# FastAPI
# ============================================================


app = FastAPI(
    title="Counselor AI",
    description=(
        "集学生手册政策问答、"
        "基础心理支持、"
        "风险告警、人工接管"
        "与微信公众号接入于一体的 "
        "AI 辅导员服务"
    ),
    version="0.6.0",
    lifespan=lifespan,
)
# ============================================================
# Admin UI
# ============================================================

from fastapi.staticfiles import StaticFiles


app.mount(
    "/admin-ui",
    StaticFiles(
        directory="src/static/admin",
        html=True,
    ),
    name="admin-ui",
)

# ============================================================
# Routers
# ============================================================


app.include_router(
    wechat_router
)

app.include_router(
    admin_router
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
    safety_level: str | None = None

    answer: str

    retrieved_sources: list[Source] = Field(
        default_factory=list
    )

    cited_sources: list[Source] = Field(
        default_factory=list
    )


# ============================================================
# Source Helpers
# ============================================================


def build_sources(
    results: list[dict],
) -> list[Source]:
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

        sources.append(
            source
        )

    return sources


def get_cited_sources(
    retrieved_sources: list[Source],
    cited_source_ids: list[str],
) -> list[Source]:
    source_map = {
        source.source_id: source
        for source in retrieved_sources
    }

    return [
        source_map[source_id]
        for source_id in cited_source_ids
        if source_id in source_map
    ]


# ============================================================
# Basic Routes
# ============================================================


@app.get("/")
def root():
    return {
        "name": "Counselor AI",
        "version": "0.6.0",
        "status": "running",
        "capabilities": [
            "policy",
            "counseling",
            "safety",
            "alerts",
            "handoff",
            "wechat",
        ],
    }


@app.get("/health")
def health():
    service = getattr(
        app.state,
        "assistant_service",
        None,
    )

    ready = (
        service is not None
    )

    return {
        "status": (
            "ok"
            if ready
            else "starting"
        ),
        "system_ready": ready,
        "wechat_route_ready": (
            any(
                getattr(
                    route,
                    "path",
                    None,
                )
                == "/wechat"
                for route in app.routes
            )
        ),
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
    service = getattr(
        app.state,
        "assistant_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI counselor system "
                "is not ready."
            ),
        )

    question = (
        request.question.strip()
    )

    if not question:
        raise HTTPException(
            status_code=400,
            detail=(
                "Question cannot be empty."
            ),
        )

    try:
        result = (
            service.handle_question(
                question
            )
        )

        intent = result[
            "intent"
        ]

        safety_level = result.get(
            "safety_level"
        )

        answer = result[
            "answer"
        ]

        retrieval_results = (
            result.get(
                "retrieval_results",
                [],
            )
        )

        cited_source_ids = (
            result.get(
                "cited_source_ids",
                [],
            )
        )

        retrieved_sources = (
            build_sources(
                retrieval_results
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
            intent=intent,
            safety_level=(
                safety_level
            ),
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