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

    # 調用 GitHub Models API (2026 標準端點)
    url = "models.inference.ai.azure.com"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "你是一個資深架構師。請根據提供的檔案結構，生成一段 Mermaid.js 的 graph TD 語法來描述軟體架構。只輸出代碼，不要解釋。"},
            {"role": "user", "content": f"這是我的專案目錄結構：\n{context}"}
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()['choices'][0]['message']['content']
    
    # 清理輸出，確保只有 Mermaid 語法
    mermaid_code = result.replace("```mermaid", "").replace("```", "").strip()
    
    with open("docs/architecture.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_code)

if __name__ == "__main__":
    generate_mermaid()
