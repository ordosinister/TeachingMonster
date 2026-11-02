# TeachingMonster — Progress

> GitHub: ordosinister/TeachingMonster
> Branch: main

## Current Focus
擴充 extractors 支援 Microsoft Word（DOCX）格式，比照 PowerPoint pipeline 建立對等的解析與 LLM extraction 流程。

## TODO
- [ ] 補充單元測試與品質檢查工具（ruff / black）
- [ ] 驗證 blueprint cache 在多次 request_id 下的命中行為
- [ ] 驗證 slide_audit → feedback → finetuning agent loop 的收斂行為
- [ ] 補充 image/run.py 的錯誤處理與重試邏輯（目前使用 while True 無上限重試）
- [ ] 驗證 extractors/word/ parser 在真實 DOCX 檔案上的圖片提取正確性
- [ ] 評估 extractors/powerpoint/ 與 extractors/word/ 共用 generation_pipeline 抽象的可能性
- [ ] 更新 registry.yaml：將 TeachingMonster 的 quality.checks 從空陣列補上基礎項目

## Done (recent)

### extractors 擴充：新增 Word DOCX parser 草稿
- [x] extraction/ → extractors/ 目錄統一並清理遺留引用（shared/pipeline.py 刪除、pptx.py → powerpoint/__init__.py 遷移）
- [x] extractors/word/__init__.py: 企業培訓語境 SYSTEM PROMPT（對照 PowerPoint 版本，改為 Word Document Analyst）
- [x] extractors/word/parser.py: DOCX 結構解析（段落含 style、表格、內嵌圖片 zip/xml 提取）
- [x] extractors/word/generation_pipeline.py: LangChain pipeline 使用 uild_standard_chat_prompt_template + image_caption model
- [x] extractors/word/main.py: 入口 un(docx_path)，含 SHA256 快取與 data/{hash}/input.json 輸出
- [x] equirements.txt: 新增 python-docx

### 全系統語境遷移：K-12 STEM → 企業內訓
- [x] lueprint/system_prompt_warehouse/background.py: 固定跨區域落差診斷 SYSTEM PROMPT（source-region → target-region）
- [x] lueprint/system_prompt_warehouse/presentation.py: 重寫為企業教案生成，加入 dependency-first sequencing、在地化改寫策略
- [x] lueprint/system_prompt_warehouse/decompress.py: 重寫為骨架 draft 豐富化，強調 teaching_adjustments 直接實作、PERSONA 語言能力約束
- [x] lueprint/agent/slide_audit/__init__.py: prereq/jargon SYSTEM PROMPT 以 COURSE_REQUIREMENT + KNOWLEDGE_GAPS + PERSONA 三角定位缺口
- [x] lueprint/agent/feedback/__init__.py: 注入 PERSONA context，Cultural Adaptation 從 PERSONA 視角評判
- [x] lueprint/agent/finetuning/__init__.py: 改寫為 gap bridger，要求直接將 SLIDE_AUDIT 缺口轉為 bridging content
- [x] lueprint/post_processing/consistency_check.py + __init__.py + generation_pipeline.py: 一致性檢查與修正 pipeline，明確區分 contradictions / coverage gaps / cultural residues 三種 issue 的修正規則
- [x] image/visual_style/__init__.py: 重寫為企業培訓視覺風格指導，移除 K-12 術語
- [x] image/image_logic/__init__.py: 重寫圖像分類決策，從「數學/物理向量圖」改為「概念圖 vs 數據可視化」
- [x] udio/__init__.py: 重寫語音風格指導，從 AP-level teacher 改為 enterprise training narrator，以 seniority 取代 grade level

### Agent 模組清理與重構
- [x] 移除 lueprint/agent/jargon_overload/、prerequisite_gap/、mathematic_coder_v2/（未使用）
- [x] eedback_v2/ → eedback/、inetuning_v2/ → inetuning/ 目錄重命名
- [x] post_processing/math_validation.py + concept_supervision.py 刪除（STEM 真理驗證不適用企業內訓）
- [x] slide/ → image/ 目錄遷移（image_logic/、image_matplotlib/、isual_style/、ender_prompt.py）
- [x] 	ts/ → udio/ 目錄遷移（un.py、generation_pipeline.py）

### Pipeline 結構統一
- [x] 所有 pipeline 統一使用 uild_standard_chat_prompt_template()（generation_pipeline.py、create_slide_pipeline、consistency_check 等）
- [x] lueprint/run.py: 新增 (course_requirement, persona) 指紋快取機制，持久化 pedagogical_state
- [x] image/run.py: 模型升級 gpt-image-2 → gpt-image-2.5-sunburst/flare，source_dir 路徑修正為 {request_id}/{cache_key}
- [x] ideo_gen/run.py: 新增 cache_key 參數，修正影片尺寸為偶數，升級輸出編碼參數（yuv420p / faststart / medium preset / 192k audio）

### Prompt 結構標準化
- [x] 所有 SYSTEM PROMPT 統一為 #Goal/#Role/#Inputs/#Rules/#Constraints/#Output Markdown 結構
- [x] 所有 Inputs 統一以 <PERSONA> 取代 <STUDENT_PERSONA>，明確包含「受眾地區、語言能力、業務/技術背景」
- [x] 移除所有 STEM/K-12 殘留術語（grade、AP-level、proof、LaTeX、algebraic、vector、physics 等）

### 已知結構性改動
- [x] lueprint/structured_output.py: 移除 subject、	arget_level、jargon、slide_type、prior_knowledge、inferred_level 欄位
- [x] lueprint/agent/context.py: AgentContext 新增 persona: str 欄位，移除 subject 相關邏輯
- [x] lueprint/run.py: 暫時停用 _save_to_cache（待驗證）

## Known Issues
- 專案尚無統一 formatter / linter（ruff / black 未配置）
- image/run.py 部分錯誤處理使用 while True 無上限重試
- extractors/word/ 尚未在真實 DOCX 上驗證圖片提取（僅語法 parse 通過）