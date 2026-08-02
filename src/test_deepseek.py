import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

if not api_key:
    raise RuntimeError(
        "没有找到 DEEPSEEK_API_KEY，请检查项目根目录下的 .env 文件。"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "system",
            "content": "你是一名校园政策问答助手。",
        },
        {
            "role": "user",
            "content": "请用一句话说明你的作用。",
        },
    ],
    extra_body={
        "thinking": {
            "type": "disabled",
        }
    },
    max_tokens=100,
)

answer = response.choices[0].message.content

if not answer:
    raise RuntimeError("DeepSeek API 返回了空内容。")

print(answer)