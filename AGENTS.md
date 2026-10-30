# AGENTS.md

> TeachingMonster 專案 Agent 工作規範（複製自 ai_orchestrator templates，依專案特性調整）。

## Project Info

- **Local path:** ../TeachingMonster
- **GitHub:** https://github.com/ordosinister/TeachingMonster
- **Stack:** Python 3.x, FastAPI / Flask, LangChain, moviepy

## Project Progress Tracking

本專案維護 PROGRESS.md（格式：Current Focus / TODO / Done (recent) / Known Issues）：

- Agent 開始任務前先讀 PROGRESS.md 了解當前進度與待辦。
- 任務若改變進度或完成 TODO 項目，**更新 PROGRESS.md 並與代碼同一個 commit**。
- Known Issues 區塊記錄用戶回報或排查中但尚未修復的問題。

## Entry Points 職責分界

本專案有兩個執行入口，職責明確區分：

### 1. service/api.py — FastAPI Web Service（對外服務）

- **角色**：生產環境/開發環境的 HTTP API 服務端點
- **啟動方式**：uvicorn service.api:app --host 0.0.0.0 --port 8000
- **對外端點**：
  - POST /v1/dev/video/generate — DEV 模式（Ollama 模型）
  - POST /v1/prod/video/generate — PROD 模式（OpenAI 模型）
  - POST /v1/files/{request_id}/video — 取得已生成影片的 S3 URL
  - POST /test — 連線測試（300s sleep，用於 ngrok 驗證）
- **處理方式**：透過 VideoWorker 非同步處理請求，回傳 presigned S3 URL
- **適用情境**：外部系統呼叫、定時任務觸發、ngrok 公開服務

### 2. 
un.py — CLI Pipeline（手動執行）

- **角色**：本地開發調試與手動批次執行的管線編排器
- **啟動方式**：python run.py --request_id <id> --requirement <text> --persona <text>
- **執行流程**：依序呼叫五階段 writers（Blueprint → Adaptation → Slide → TTS → Video）
- **輸出**：logs/pipeline.log + 終端輸出
- **適用情境**：本地開發測試、單次手動生成、排查 pipeline 問題
- **預設行為**：未給參數時以 data/celery_0000_0000000010/input.json 跑測試模式

**注意**：
un.py 的 main() 函式由 service/worker.py 內的 VideoWorker.process_request() 呼叫；兩個入口共享同一套 pipeline 邏輯，只差在觸發方式（HTTP API vs CLI）。

## Encoding Pitfalls (Windows / PowerShell)

This repository contains Traditional/Simplified Chinese text. When editing on Windows with PowerShell:

- pply_patch may mangle CJK content or report 
equires a UTF-8 PATCH argument; PowerShell here-strings can also fail encoding validation.
- Mojibake (??) means the file was saved with the wrong code page. Check bytes, not console output.

**Workaround:** write the edit as a temp Python script saved explicitly as UTF-8, use encoding="utf-8" for all reads/writes, then verify with st.parse and search for leftover ??.

## Python Quality Checks (for CI)

Inspect pyproject.toml before choosing scope. After modifying Python code:

`powershell
python -m ruff check .
python -m black --check .
python -m mypy .
`

Do not weaken rules or suppress errors to pass checks. Distinguish pre-existing failures from regressions. A task is not verified if any required check is unexecuted or blocked.

## Failure Handling Protocol

1. Preserve file content and encoding; make the smallest necessary changes.
2. Diagnose failures before retrying — never repeat the same failed command without a specific reason why the next attempt should succeed.
3. For the same underlying failure, allow at most **two attempts**; then switch method or report the blocker.
4. No unbounded retry/polling loops; do not reinstall dependencies or touch unrelated files to work around a local failure.
5. Verify all changes before reporting completion. Never claim success without evidence.

**Stop conditions:** recurring encoding/patch errors; repeated failure with no new diagnostics; file integrity cannot be established; a repair risks overwriting unrelated changes; a validation tool cannot run.
