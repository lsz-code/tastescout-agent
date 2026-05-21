from openai import OpenAI

LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_API_KEY="sk-577200917d7e43f8b9142ed0d5989624"
LLM_MODEL="qwen3.6-plus"

client = OpenAI(
    base_url=LLM_BASE_URL, 
    api_key=LLM_API_KEY,
    )

response=client.chat.completions.create(
    model=LLM_MODEL,
    messages=[
        {"role": "system", "content": "你是我的人工智能助手，协助我完成各种任务。"},
        {"role": "user", "content": "请介绍一下自己。"},
    ],
)

print(response.choices[0].message.content)