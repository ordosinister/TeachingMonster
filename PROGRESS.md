# TeachingMonster — Progress

> GitHub: ordosinister/TeachingMonster
> Branch: dev

## Current Focus
將全系統從 K-12 STEM 教育語境遷移至「企業內部培訓、跨區域受眾適配」語境。所有 SYSTEM PROMPT 與 pipeline 已完成重構，正進行目錄結構統一與遺留引用清理。

## TODO
- [ ] 補充單元測試與品質檢查工具（ruff / black）
- [ ] 驗證 blueprint cache 在多次 request_id 下的命中行為
- [ ] 驗證 slide_audit → feedback → finetuning agent loop 的收斂行為
- [ ] 補充 image/run.py 的錯誤處理與重試邏輯（目前使用 while True 無上限重試）
- [ ] 評估是否將 extraction/ 也遷移至 src/logic/extraction/ 統一結構

## Done (recent)

### 全系統語境遷移：K-12 STEM → 企業內訓
- [x] `blueprint/system_prompt_warehouse/background.py`: 固定跨區域落差診斷 SYSTEM PROMPT（source-region → target-region）
- [x] `blueprint/system_prompt_warehouse/presentation.py`: 重寫為企業教案生成，加入 dependency-first sequencing、在地化改寫策略
- [x] `blueprint/system_prompt_warehouse/decompress.py`: 重寫為骨架 draft 豐富化，強調 teaching_adjustments 直接實作、PERSONA 語言能力約束
- [x] `blueprint/agent/slide_audit/__init__.py`: prereq/jargon SYSTEM PROMPT 以 COURSE_REQUIREMENT + KNOWLEDGE_GAPS + PERSONA 三角定位缺口
- [x] `blueprint/agent/feedback/__init__.py`: 注入 PERSONA context，Cultural Adaptation 從 PERSONA 視角評判
- [x] `blueprint/agent/finetuning/__init__.py`: 改寫為 gap bridger，要求直接將 SLIDE_AUDIT 缺口轉為 bridging content
- [x] `blueprint/post_processing/consistency_check.py` + `__init__.py` + `generation_pipeline.py`: 一致性檢查與修正 pipeline，明確區分 contradictions / coverage gaps / cultural residues 三種 issue 的修正規則
- [x] `image/visual_style/__init__.py`: 重寫為企業培訓視覺風格指導，移除 K-12 術語
- [x] `image/image_logic/__init__.py`: 重寫圖像分類決策，從「數學/物理向量圖」改為「概念圖 vs 數據可視化」
- [x] `audio/__init__.py`: 重寫語音風格指導，從 AP-level teacher 改為 enterprise training narrator，以 seniority 取代 grade level

### Agent 模組清理與重構
- [x] 移除 `blueprint/agent/jargon_overload/`、`prerequisite_gap/`、`mathematic_coder_v2/`（未使用）
- [x] `feedback_v2/` → `feedback/`、`finetuning_v2/` → `finetuning/` 目錄重命名
- [x] `post_processing/math_validation.py` + `concept_supervision.py` 刪除（STEM 真理驗證不適用企業內訓）
- [x] `slide/` → `image/` 目錄遷移（`image_logic/`、`image_matplotlib/`、`visual_style/`、`render_prompt.py`）
- [x] `tts/` → `audio/` 目錄遷移（`run.py`、`generation_pipeline.py`）
- [x] `extraction/system_prompts/` → `extraction/system_prompt_warehouse/` 目錄統一

### Pipeline 結構統一
- [x] 所有 pipeline 統一使用 `build_standard_chat_prompt_template()`（`generation_pipeline.py`、`create_slide_pipeline`、`consistency_check` 等）
- [x] `blueprint/run.py`: 新增 `(course_requirement, persona)` 指紋快取機制，持久化 `pedagogical_state`
- [x] `image/run.py`: 模型升級 `gpt-image-2` → `gpt-image-2.5-sunburst/flare`，`source_dir` 路徑修正為 `{request_id}/{cache_key}`
- [x] `video_gen/run.py`: 新增 `cache_key` 參數，修正影片尺寸為偶數，升級輸出編碼參數（yuv420p / faststart / medium preset / 192k audio）

### Prompt 結構標準化
- [x] 所有 SYSTEM PROMPT 統一為 `#Goal/#Role/#Inputs/#Rules/#Constraints/#Output` Markdown 結構
- [x] 所有 Inputs 統一以 `<PERSONA>` 取代 `<STUDENT_PERSONA>`，明確包含「受眾地區、語言能力、業務/技術背景」
- [x] 移除所有 STEM/K-12 殘留術語（grade、AP-level、proof、LaTeX、algebraic、vector、physics 等）

### 已知結構性改動
- [x] `blueprint/structured_output.py`: 移除 `subject`、`target_level`、`jargon`、`slide_type`、`prior_knowledge`、`inferred_level` 欄位
- [x] `blueprint/agent/context.py`: `AgentContext` 新增 `persona: str` 欄位，移除 `subject` 相關邏輯
- [x] `blueprint/run.py`: 暫時停用 `_save_to_cache`（待驗證）

## Known Issues
- 專案尚無統一 formatter / linter（ruff / black 未配置）
- image/run.py 部分錯誤處理使用 `while True` 無上限重試
- extraction/ 目錄結構與 src/logic/ 不完全一致，未來可能統一
