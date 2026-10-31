# TeachingMonster — Progress

> GitHub: ordosinister/TeachingMonster

## Current Focus
Cleanup blueprint agent modules: merge indirectly-used prompts into slide_audit, delete unused agent directories, and fix downstream imports.

## TODO
- [ ] 完成 extraction 模組整合測試
- [ ] 補充 .gitignore 涵蓋 credentials、data/、venv、__pycache__
- [ ] 補充單元測試與品質檢查工具（ruff / black）
- [ ] 驗證 blueprint cache 在多次 request_id 下的命中行為

## Done (recent)
- [x] 移除 post_processing/math_validation.py（STEM 真理驗證不適用企業內訓）
- [x] 移除 post_processing/concept_supervision.py（K-12 事實查核不適用企業內訓）
- [x] 新建 post_processing/consistency_check.py：企業內訓一致性檢查（內部一致性、需求覆蓋率、文化適配殘留）
- [x] 更新 run.py：用 run_consistency_check 取代 run_math_validation + run_concept_supervision
- [x] blueprint/agent/ 清理: 移除 jargon_overload/、prerequisite_gap/、mathematic_coder_v2/ 未使用模組
- [x] 將 prereq_SYSTEM_PROMPT 與 jargon_SYSTEM_PROMPT 合併進 slide_audit/__init__.py，修復 slide_audit/agent_tool.py 引用
- [x] post_processing/math_validation.py 內聯 MATH_SYSTEM_PROMPT，移除對已刪除模組的依賴
- [x] blueprint/run.py: 新增 (course_requirement, persona) 指紋快取機制，支援同一 course_requirement 對應多個 persona
- [x] 釐清入口職責分界：service/api.py（FastAPI Web Service，對外 API）vs run.py（CLI 手動 Pipeline，本地調試/批次執行）
- [x] 建立 extraction/ 與 extraction/powerpoint/、extraction/shared/、extraction/system_prompts/ 子模組
- [x] 將 src/io/path_definition.py 搬遷至 src/path/path_definition.py
- [x] 新增 .gitignore、AGENTS.md、PROGRESS.md

## Known Issues
- 專案尚無統一 formatter / linter（ruff / black 未配置）
- __pycache__ 與 data/ 目前未被 .gitignore 過濾（已於本次加入）