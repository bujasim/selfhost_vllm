from openai import OpenAI


def main() -> None:
    client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")
    response = client.chat.completions.create(
        model="Qwen/Qwen3.5-0.8B",
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        max_tokens=16,
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    print(response.choices[0].message.content)
    print(response.usage)


if __name__ == "__main__":
    main()
