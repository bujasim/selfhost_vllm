from openai import OpenAI

from runtime_config import get_client_host, load_runtime_config


CONFIG = load_runtime_config()
BASE_URL = f"http://{get_client_host(CONFIG)}:{CONFIG['PORT']}/v1"
MODEL = CONFIG["MODEL"]

def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key="EMPTY")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        max_tokens=16,
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    print(response.choices[0].message.content)
    print(response.usage)


if __name__ == "__main__":
    main()
