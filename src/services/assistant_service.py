from typing import Any

from src.counseling.counselor import Counselor
from src.counseling.crisis_responder import CrisisResponder
from src.counseling.safety_classifier import SafetyClassifier
from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever
from src.routing.intent_router import IntentRouter

from src.conversation.store import (
    ConversationStore,
)


class AssistantService:
    def __init__(self) -> None:
        self.retriever = Retriever()
        self.deepseek_client = DeepSeekClient()
        self.intent_router = IntentRouter()
        self.counselor = Counselor()
        self.safety_classifier = SafetyClassifier()
        self.crisis_responder = CrisisResponder()
        self.conversation_store = ConversationStore()

    def handle_question(
        self,
        question: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        question = question.strip()

        if not question:
            return {
                "intent": "other",
                "safety_level": None,
                "answer": "请输入一个问题。",
                "retrieval_results": [],
                "cited_source_ids": [],
            }

        history: list[dict[str, str]] = []

        if conversation_id:
            history = (
                self.conversation_store
                .get_history(
                    conversation_id
                )
            )

        # ====================================================
        # 1. Intent Routing
        # ====================================================

        intent = self.intent_router.classify(
        question
        )

        if (
            intent == "other"
            and history
        ):
            context_intent = (
                self.intent_router
                .classify_with_context(
                    question,
                    history,
                )
            )

            if context_intent != "other":
                print(
                    "[CONTEXT ROUTER] "
                    f"{question} "
                    f"-> {context_intent}"
                )

                intent = context_intent

        print(
            f"[ROUTER] {question} -> {intent}"
        )

        # ====================================================
        # 2. Counseling
        # ====================================================

        if intent == "counseling":
            safety_level = (
                self.safety_classifier.classify(
                    question
                )
            )

            print(
                f"[SAFETY] {question} "
                f"-> {safety_level}"
            )

            # ------------------------------------------------
            # Crisis
            # ------------------------------------------------

            if safety_level == "crisis":
                answer = (
                    self.crisis_responder.respond(
                        question
                    )
                )

            # ------------------------------------------------
            # Concern
            #
            # 不再调用 Counselor。
            # 微信被动回复有时间限制，
            # concern 如果再次调用 LLM，
            # 整条链路可能因为耗时过长导致微信重试。
            # ------------------------------------------------

            elif safety_level == "concern":
                answer = (
                    "听起来你最近的状态已经比较辛苦了。"
                    "如果这种低落、无力，或者什么都不想做的"
                    "感觉已经持续了一段时间，"
                    "或者明显影响到睡眠、饮食、学习和日常生活，"
                    "建议不要一个人硬撑。"
                    "\n\n"
                    "可以尽快找一个现实中可信任的人聊聊，"
                    "比如朋友、家人、老师或辅导员，"
                    "也可以考虑联系学校的专业心理支持资源。"
                    "\n\n"
                    "如果你愿意，也可以继续告诉我，"
                    "最近最困扰你的事情是什么。"
                )

            # ------------------------------------------------
            # Normal
            # ------------------------------------------------

            else:
                answer = self.counselor.answer(
                    question,
                    history=history,
                )

            return {
                "intent": "counseling",
                "safety_level": safety_level,
                "answer": answer,
                "retrieval_results": [],
                "cited_source_ids": [],
            }

        # ====================================================
        # 3. Other
        # ====================================================

        if intent == "other":
            return {
                "intent": "other",
                "safety_level": None,
                "answer": (
                    "这个问题目前不属于我可以处理的"
                    "学生政策问答或基础心理支持范围。"
                    "\n\n"
                    "你可以询问学生手册相关规定，"
                    "例如请假、学籍、选课、成绩、"
                    "奖学金、毕业等问题；"
                    "也可以和我聊聊学习压力、情绪、"
                    "焦虑、人际关系等困扰。"
                ),
                "retrieval_results": [],
                "cited_source_ids": [],
            }

        # ====================================================
        # 4. Policy
        # ====================================================

        results = self.retriever.retrieve(
            question
        )

        llm_result = (
            self.deepseek_client.answer(
                question=question,
                retrieval_results=results,
            )
        )

        return {
            "intent": "policy",
            "safety_level": None,
            "answer": llm_result["answer"],
            "retrieval_results": results,
            "cited_source_ids": (
                llm_result.get(
                    "cited_source_ids",
                    [],
                )
            ),
        }