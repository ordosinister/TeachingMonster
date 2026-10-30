# TeachingMonster — Progress

> GitHub: ordosinister/TeachingMonster

## Current Focus
將 extraction 模組與 path 模組重構後首次 commit，建立專案追蹤文件。

## TODO
- [ ] 完成 extraction 模組整合測試
- [ ] 補充 .gitignore 涵蓋 credentials、data/、venv、__pycache__
- [ ] 釐清 service/api.py 與 run.py 的入口職責分界
- [ ] 補充單元測試與品質檢查工具（ruff / black）

## Done (recent)
- [x] 建立 extraction/ 與 extraction/powerpoint/、extraction/shared/、extraction/system_prompts/ 子模組
- [x] 將 src/io/path_definition.py 搬遷至 src/path/path_definition.py
- [x] 新增 .gitignore、AGENTS.md、PROGRESS.md

## Known Issues
- 專案尚無統一 formatter / linter（ruff / black 未配置）
- __pycache__ 與 data/ 目前未被 .gitignore 過濾（已於本次加入）
