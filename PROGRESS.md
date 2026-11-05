# TeachingMonster — Progress

> GitHub: ordosinister/TeachingMonster
> Branch: main

## Current Focus
整合 extractors 三大格式（PowerPoint / PDF / Word）的 pipeline，統一為 MessagesPlaceholder 架構；驗證 PDF 頁面圖像解析在真實文件上的正確性。

## TODO
- [ ] 補充單元測試與品質檢查工具（ruff / black）
- [ ] 驗證 blueprint cache 在多次 request_id 下的命中行為
- [ ] 驗證 slide_audit → feedback → finetuning agent loop 的收斂行為
- [ ] 補充 image/run.py 的錯誤處理與重試邏輯（目前使用 while True 無上限重試）
- [ ] 驗證 extractors/pdf/ parser 在真實 PDF 上的圖像解析與內容提取正確性
- [ ] 驗證 extractors/word/ parser 在真實 DOCX 上的圖片提取正確性
- [ ] 評估 extractors/powerpoint/ 與 extractors/word/ 共用 generation_pipeline 抽象的可能性
- [ ] 更新 registry.yaml：將 TeachingMonster 的 quality.checks 從空陣列補上基礎項目

## Done (recent)

### extractors 統一重構：PowerPoint / PDF / Word pipeline 標準化
- [x] extractors/powerpoint/generation_pipeline.py: 改為 ChatPromptTemplate + MessagesPlaceholder（移除 build_standard_chat_prompt_template 依賴）
- [x] extractors/powerpoint/main.py: print() → logging.info()，加入 request_id / 耗時記錄
- [x] extractors/powerpoint/parser.py: 移除 win32com / pptx_to_pdf 廢棄程式碼
- [x] extractors/pdf/__init__.py: **新增 PDF 專屬 SYSTEM PROMPT**（參照 PowerPoint 結構，改為頁面圖像輸入）
- [x] extractors/pdf/parser.py: **全面重構** — 移除 PowerPoint 結構化解析，改為 pymupdf 頁面轉 JPEG Base64
- [x] extractors/pdf/generation_pipeline.py: 改為 ChatPromptTemplate + MessagesPlaceholder
- [x] extractors/pdf/main.py: 改為 logging、加入 request_id 記錄、修正 hash 邏輯
- [x] extractors/word/generation_pipeline.py: 改為 ChatPromptTemplate + MessagesPlaceholder
- [x] extractors/word/main.py: print() → logging.info()，加入 request_id 記錄，測試檔案改為 `勞工道德管理培訓教材.docx`
- [x] extractors/word/parser.py: 加入 subprocess import（支援外部工具呼叫）
- [x] requirements.txt: 修正依賴格式（pymupdf / python-docx / docling 分行）
- [x] run.py: 改為支援 pptx/pdf 自動判斷入口、DEV 模式、測試檔案改為 PDF

### writers 修正與優化
- [x] src/logic/writers/blueprint/run.py: 修正 `create_decompression_pipeline` 函數名（原為 `create_decompress_pipeline`）；json.dump 加入 `ensure_ascii=False`
- [x] src/logic/writers/image/run.py: OpenAI image generation 加入固定 `size="1792x1008"`
- [x] src/logic/writers/video_gen/run.py: 加入 PIL / numpy import；改為 logging.info；移除 cropped 尺寸修正邏輯（改由上游控制）；暫時註解掉 preset / audio_bitrate / movflags / logger 參數

### extractors 擴充：新增 Word DOCX parser 草稿
- [x] extraction/ → extractors/ 目錄統一並清理遺留引用（shared/pipeline.py 刪除、pptx.py → powerpoint/__init__.py 遷移）
- [x] extractors/word/__init__.py: 企業培訓語境 SYSTEM PROMPT（對照 PowerPoint 版本，改為 Word Document Analyst）
- [x] extractors/word/parser.py: DOCX 結構解析（段落含 style、表格、內嵌圖片 zip/xml 提取）
- [x] extractors/word/generation_pipeline.py: LangChain pipeline 使用 build_standard_chat_prompt_template + image_caption model
- [x] extractors/word/main.py: 入口 run(docx_path)，含 SHA256 快取與 data/{hash}/input.json 輸出
- [x] requirements.txt: 新增 python-docx

### 全系統語境遷移：K-12 STEM → 企業內訓
- [x] blueprint/system_prompt_warehouse/background.py: 固定跨區域落差診斷 SYSTEM PROMPT（source-region → target-region）
- [x] blueprint/system_prompt_warehouse/presentation.py: 重寫為企業教案生成，加入 dependency-first sequencing、在地化改寫策略
- [x] blueprint/system_prompt_warehouse/decompress.py: 重寫為骨架 draft 豐富化，強調 teaching_adjustments 直接實作、PERSONA 語言能力約束
- [x] blueprint/agent/slide_audit/__init__.py: prereq/jargon SYSTEM PROMPT 以 COURSE_REQUIREMENT + KNOWLEDGE_GAPS + PERSONA 三角定位缺口
- [x] blueprint/agent/feedback/__init__.py: 注入 PERSONA context，Cultural Adaptation 從 PERSONA 視角評判
- [x] blueprint/agent/finetuning/__init__.py: 改寫為 gap bridger，要求直接將 SLIDE_AUDIT 缺口轉為 bridging content
- [x] blueprint/post_processing/consistency_check.py + __init__.py + generation_pipeline.py: 一致性檢查與修正 pipeline，明確區分 contradictions / coverage gaps / cultural residues 三種 issue 的修正規則
- [x] image/visual_style/__init__.py: 重寫為企業培訓視覺風格指導，移除 K-12 術語
- [x] image/image_logic/__init__.py: 重寫圖像分類決策，從「數學/物理向量圖」改為「概念圖 vs 數據可視化」
- [x] audio/__init__.py: 重寫語音風格指導，從 AP-level teacher 改為 enterprise training narrator，以 seniority 取代 grade level

### Agent 模組清理與重構
- [x] 移除 blueprint/agent/jargon_overload/、prerequisite_gap/、mathematic_coder_v2/（未使用）
- [x] feedback_v2/ → feedback/、finetuning_v2/ → finetuning/ 目錄重命名
- [x] post_processing/math_validation.py + concept_supervision.py 刪除（STEM 真理驗證不適用企業內訓）
- [x] slide/ → image/ 目錄遷移（image_logic/、image_matplotlib/、visual_style/、render_prompt.py）
- [x] tts/ → audio/ 目錄遷移（run.py、generation_pipeline.py）

### Pipeline 結構統一
- [x] 所有 pipeline 統一使用 build_standard_chat_prompt_template()（generation_pipeline.py、create_slide_pipeline、consistency_check 等）
- [x] blueprint/run.py: 新增 (course_requirement, persona) 指紋快取機制，持久化 pedagogical_state
- [x] image/run.py: 模型升級 gpt-image-2 → gpt-image-2.5-sunburst/flare，source_dir 路徑修正為 {request_id}/{cache_key}
- [x] video_gen/run.py: 新增 cache_key 參數，修正影片尺寸為偶數，升級輸出編碼參數（yuv420p / faststart / medium preset / 192k audio）

### Prompt 結構標準化
- [x] 所有 SYSTEM PROMPT 統一為 #Goal/#Role/#Inputs/#Rules/#Constraints/#Output Markdown 結構
- [x] 所有 Inputs 統一以 <PERSONA> 取代 <STUDENT_PERSONA>，明確包含「受眾地區、語言能力、業務/技術背景」
- [x] 移除所有 STEM/K-12 殘留術語（grade、AP-level、proof、LaTeX、algebraic、vector、physics 等）

### 已知結構性改動
- [x] blueprint/structured_output.py: 移除 subject、target_level、jargon、slide_type、prior_knowledge、inferred_level 欄位
- [x] blueprint/agent/context.py: AgentContext 新增 persona: str 欄位，移除 subject 相關邏輯
- [x] blueprint/run.py: 暫時停用 _save_to_cache（待驗證）

## Known Issues
- 專案尚無統一 formatter / linter（ruff / black 未配置）
- image/run.py 部分錯誤處理使用 while True 無上限重試
- extractors/pdf/ parser 改用 pymupdf 頁面圖像後，尚未在真實 PDF 上驗證內容提取正確性（特別是表格與圖表）
- extractors/word/ 尚未在真實 DOCX 上驗證圖片提取（僅語法 parse 通過）
- video_gen/run.py 暫時註解掉 preset/audio_bitrate/movflags/logger，輸出品質待驗證