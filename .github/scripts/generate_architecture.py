import os
import requests

def generate_mermaid():
    token = os.getenv("GITHUB_TOKEN")
    # 讀取當前目錄下的主要結構 (排除不需要的資料夾)
    files_tree = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or "node_modules" in root: continue
        files_tree.append(f"{root}\n" + "\n".join([f"  - {f}" for f in files[:5]]))
    
    context = "\n".join(files_tree[:50]) # 限制長度以避免 Token 超限

    # Call GitHub Models inference API
    token = os.getenv("MODELS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("Environment variable MODELS_TOKEN (or GITHUB_TOKEN) is required with 'models: read' scope.")

    org = os.getenv("MODELS_ORG")  # optional: set to attribute requests to an organization
    model = os.getenv("MODELS_MODEL") or "openai/gpt-4.1"

    if org:
        url = f"https://models.github.ai/orgs/{org}/inference/chat/completions"
    else:
        url = "https://models.github.ai/inference/chat/completions"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一個資深架構師。請根據提供的檔案結構，生成一段 Mermaid.js 的 graph TD 語法來描述軟體架構。只輸出代碼，不要解釋。"},
            {"role": "user", "content": f"這是我的專案目錄結構：\n{context}"}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        raise SystemExit(f"Request to GitHub Models failed: {e}")

    try:
        data = response.json()
    except ValueError:
        raise SystemExit("Response did not contain valid JSON")

    # Extract text from GitHub Models response
    result = ""
    if isinstance(data, dict):
        choices = data.get("choices", [])
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                msg = first.get("message", {})
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str):
                        result = content
                    elif isinstance(content, list):
                        result = "\n".join([c for c in content if isinstance(c, str)])
                if not result:
                    text = first.get("text")
                    if isinstance(text, str):
                        result = text

    result = result or response.text

    # 清理輸出，確保只有 Mermaid 語法
    mermaid_code = result.replace("```mermaid", "").replace("```", "").strip()

    os.makedirs("docs", exist_ok=True)
    with open("docs/architecture.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_code)

if __name__ == "__main__":
    generate_mermaid()
