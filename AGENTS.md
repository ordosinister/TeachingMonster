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
