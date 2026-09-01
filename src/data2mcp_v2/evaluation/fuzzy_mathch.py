from data2mcp_v2.config import EvaluationConfig, LLMConfig
from data2mcp_v2.utils.llm_api import ChatModel


def llm_fuzzy_match(
    evaluation_config: EvaluationConfig, pred: str, reference: str, question: str
):
    """Check whether the prediction matches the reference with GPT4-turbo"""
    messages: list = []
    message = "Help a teacher to grade the answer of a student given a question. Keep in mind that the student may use different phrasing or wording to answer the question. The goal is to evaluate whether the answer is semantically equivalent to the reference answer.\n"
    message += f"question: {question}\n"
    message += f"reference answer: {reference}\n"
    message += "all the string 'N/A' that you see is a special sequence that means 'not achievable'\n"
    message += f"student answer: {pred}\n"
    message += "Conclude the judgement by correct/incorrect/partially correct."
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": message},
    ]
    llm_config: LLMConfig = evaluation_config.llm
    llm = ChatModel(
        model_name=llm_config.model,
        model_url=llm_config.base_url,
        api_key=llm_config.api_key,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        timeout=llm_config.timeout_seconds,
    )
    response = llm.chat_with_retry(messages).choices[0].message.content.lower()
    if "partially correct" in response or "incorrect" in response:
        return 0.0, response
    else:
        assert "correct" in response
        return 1.0, response
