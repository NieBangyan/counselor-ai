from typing import Any

from src.counseling.counselor import Counselor
from src.counseling.crisis_responder import CrisisResponder
from src.counseling.safety_classifier import SafetyClassifier
from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever
from src.routing.intent_router import IntentRouter


class AssistantService:
    def __init__(self) -> None:
        self.retriever = Retriever()
        self.deepseek_client = DeepSeekClient()
        self.intent_router = IntentRouter()
        self.counselor = Counselor()
        self.safety_classifier = SafetyClassifier()
        self.crisis_responder = CrisisResponder()

    def handle_question(
        self,
        question: str,
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

        intent = self.intent_router.classify(
            question
        )

        print(
            f"[ROUTER] {question} -> {intent}"
        )

        # ====================================================
        # Counseling
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

            if safety_level == "crisis":
                answer = (
                    self.crisis_responder.respond(
                        question
                    )
                )

            elif safety_level == "concern":
                answer = self.counselor.answer(
                    question
                )

                answer += (
                    "\n\n"
                    "另外，从你现在描述的状态来看，"
                    "如果这种感受已经持续了一段时间，"
                    "或者明显影响到睡眠、饮食、学习和日常生活，"
                    "建议你尽快和现实中可信任的人谈一谈，"
                    "例如朋友、家人、老师、辅导员，"
                    "也可以考虑联系学校的专业心理支持资源。"
                )

            else:
                answer = self.counselor.answer(
                    question
                )

            return {
                "intent": "counseling",
                "safety_level": safety_level,
                "answer": answer,
                "retrieval_results": [],
                "cited_source_ids": [],
            }

        # ====================================================
        # Other
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
        # Policy
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