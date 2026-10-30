# TeachingMonster — Progress

> GitHub: ordosinister/TeachingMonster

## Current Focus
為 blueprint/run.py 新增 (course_requirement, persona) 指紋快取，避免相同組合重複執行 LLM pipeline。

## TODO
- [ ] 完成 extraction 模組整合測試
- [ ] 補充 .gitignore 涵蓋 credentials、data/、venv、__pycache__
- [ ] 補充單元測試與品質檢查工具（ruff / black）
- [ ] 驗證 blueprint cache 在多次 request_id 下的命中行為

## Done (recent)
- [x] blueprint/run.py: 新增 (course_requirement, persona) 指紋快取機制，支援同一 course_requirement 對應多個 persona
- [x] 釐清入口職責分界：service/api.py（FastAPI Web Service，對外 API）vs run.py（CLI 手動 Pipeline，本地調試/批次執行）
- [x] 建立 extraction/ 與 extraction/powerpoint/、extraction/shared/、extraction/system_prompts/ 子模組
- [x] 將 src/io/path_definition.py 搬遷至 src/path/path_definition.py
- [x] 新增 .gitignore、AGENTS.md、PROGRESS.md

## Known Issues
- 專案尚無統一 formatter / linter（ruff / black 未配置）
- __pycache__ 與 data/ 目前未被 .gitignore 過濾（已於本次加入）
