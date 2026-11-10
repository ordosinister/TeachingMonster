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

本專案有三個執行入口，對應不同 pipeline：

### 1. service/api.py — FastAPI Web Service（對外服務）

- **角色**：生產環境/開發環境的 HTTP API 服務端點
- **啟動方式**：uvicorn service.api:app --host 0.0.0.0 --port 8000
- **對外端點**：
  - POST /v1/dev/video/generate — DEV 模式（Ollama 模型）
  - POST /v1/prod/video/generate — PROD 模式（OpenAI 模型）
  - POST /v1/files/{request_id}/video — 取得已生成影片的 S3 URL
  - POST /test — 連線測試（300s sleep，用於 ngrok 驗證）
- **處理方式**：透過 VideoWorker 非同步處理請求，回傳 presigned S3 URL
- **實際呼叫**：`service/worker.py` → `src.pipeline.run.run_pipeline()`（HTML slide pipeline，含 blueprint + layout + image + audio + render）
- **適用情境**：外部系統呼叫、定時任務觸發、ngrok 公開服務

### 2. src/pipeline/run.py — HTML Slide Pipeline（主要 production pipeline）

- **角色**：現行 production pipeline，生成 HTML 投影片 + AI 圖像 + TTS 音訊 + Playwright 渲染
- **啟動方式**：
  ```python
  from src.pipeline.run import run_pipeline
  await run_pipeline(user_input="...", request_id="...", persona="...", env="DEV")
  ```
- **執行流程**：
  1. `src.blueprint.run` — 可靠 blueprint 內容生成
  2. `src.pipeline.image_generator.visual_style` — 統一視覺風格
  3. `src.pipeline.slide_layout` — 兩階段排版（image prompt → HTML layout）
  4. `src.pipeline.validator` — HTML 驗證
  5. `src.pipeline.image_generator` — 圖像生成
  6. `src.pipeline.audio_generator` — TTS 音訊生成
  7. `src.pipeline.html_embedder` + `src.pipeline.renderer` — HTML embed + Playwright 錄製
- **輸出**：`data/{request_id}/{cache_key}/final_video_path`
- **適用情境**：production 影片生成、service/api.py 後端呼叫

### 3. src/sop/run.py — SOP Document Reader Pipeline（PDF → 圖 + 音 + 影片）

- **角色**：讀取 PDF 文件，每頁轉圖 + 語音旁白 → 合成影片
- **啟動方式**：`python -m src.sop.run`
- **執行流程**：
  1. `src.sop.extractors.pdf` — PDF 頁面提取 + OCR
  2. `src.sop.audio.run` — 每頁生成 TTS 語音旁白（同時執行 PDF → PNG 圖片轉換）
  3. `src.sop.video_gen.run` — 圖片與音訊合成 MP4
- **適用情境**：既有文件轉教學影片、SOP 文件語音化

### 4. legacy/v1/run.py — 舊版 CLI Pipeline（已封存）

- **角色**：第一版 pipeline，直接生成靜態圖片 + moviepy 合成（無 HTML 投影片架構）
- **啟動方式**：`python legacy/v1/run.py`
- **執行流程**：Blueprint → Adaptation → Image → TTS → Video（moviepy）
- **狀態**：已封存，僅供參考與問題排查

### 5. poc/run_concept.py — 概念驗證腳本

- **角色**：早期概念驗證，使用簡化 `poc.slide_content` 生成器（非 `src.blueprint`）
- **適用情境**：快速測試 slide layout / image generation 邏輯，不經過完整 blueprint

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
