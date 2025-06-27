import requests


def test_chat():
    url = "http://localhost:8001/chat/completions/stream"
    data = {
        "repo_url": "https://github.com/AsyncFuncAI/deepwiki-open",
        "messages": [
            {
                "role": "user",
                "content": "how backend process when user chat to repo, focus on how RAG works",
            }
        ],
    }
    response = requests.post(url, json=data)
    print(response.text)


if __name__ == "__main__":
    test_chat()
