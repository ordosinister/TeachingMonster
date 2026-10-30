# TeachingMonster

![Cover](presentation/Cover.png)

> An automated educational video generation pipeline that transforms a course requirement and student persona into a fully narrated video presentation — powered by multiple AI models.
>
> 一套全自動 AI 教學影片生成系統：接收課程需求與學生人物誌，無需任何人為介入，端到端產出附語音旁白的教學投影片影片。

---

## Table of Contents / 目錄

- [Architecture Overview / 架構總覽](#architecture-overview--架構總覽)
- [Pipeline Stages / 管線階段](#pipeline-stages--管線階段)
  - [Stage 1: Blueprint Generation / 課程藍圖生成](#stage-1-blueprint-generation--課程藍圖生成)
  - [Stage 2: Adaptation Layer / 適應層改寫](#stage-2-adaptation-layer--適應層改寫)
  - [Stage 3: Slide Image Generation / 投影片圖像生成](#stage-3-slide-image-generation--投影片圖像生成)
  - [Stage 4: TTS Audio Generation / 語音合成](#stage-4-tts-audio-generation--語音合成)
  - [Stage 5: Video Assembly / 影片組裝](#stage-5-video-assembly--影片組裝)
- [Pedagogical Design / 教學設計](#pedagogical-design--教學設計)
- [Third-Party API Services / 第三方 API 服務](#third-party-api-services--第三方-api-服務)
- [API Reference / API 參考](#api-reference--api-參考)
- [Setup & Deployment / 環境安裝與部署](#setup--deployment--環境安裝與部署)
- [Exposing the Service / 公開服務](#exposing-the-service--公開服務)
- [Data Flow / 資料流](#data-flow--資料流)
- [Project Structure / 專案結構](#project-structure--專案結構)

---

## Architecture Overview / 架構總覽

TeachingMonster is a **FastAPI microservice** backed by a five-stage AI pipeline. A single synchronous HTTP request runs the full pipeline end-to-end and returns the final video URL in the response.

TeachingMonster 是一個以 **FastAPI 微服務** 為基礎的系統，內部串接一條五階段 AI 管線。單次 HTTP 請求即同步執行完整管線，並在回應中回傳最終影片的下載 URL。

```text
Client Request / 客戶端請求
      |
      v
[ FastAPI (service/api.py) ]
      |
      v
[ VideoWorker (service/worker.py) ]
      |
      |  asyncio.to_thread()
      v
[ Pipeline Orchestrator / 管線編排器 (run.py) ]
      |
      |-- Stage 1: Blueprint Generation / 課程藍圖生成
      |-- Stage 2: Adaptation Layer / 適應層改寫
      |-- Stage 3: Slide Image Generation / 投影片圖像生成
      |-- Stage 4: TTS Audio Generation / 語音合成
      |-- Stage 5: Video Assembly / 影片組裝
      |
      v
[ CloudStorage (service/storage.py) ]
      |
      v
 S3 Presigned URL --> returned to client / 回傳客戶端
```

### Key Components / 核心組件

| Module / 模組 | Role / 角色 |
|---|---|
| `service/api.py` | FastAPI server with video generation and retrieval endpoints / FastAPI 伺服器，提供影片生成與取回端點 |
| `service/worker.py` | Background pipeline executor wrapping `asyncio.to_thread()` / 背景管線執行器，封裝 `asyncio.to_thread()` |
| `service/storage.py` | AWS S3 upload with SigV4 presigned URLs / AWS S3 上傳與 SigV4 預簽名 URL |
| `main.py` | Master pipeline orchestrator (5 stages) / 主管線編排器（5 階段） |
| `model_orchestration.py` | DEV/PROD model configuration registry / DEV/PROD 雙環境模型配置註冊表 |
| `initialization.py` | API key and credential loader from `config/credentials.ini` / 從設定檔載入 API 金鑰 |

---

## Pipeline Stages / 管線階段

### Stage 1: Blueprint Generation / 課程藍圖生成

The "instructional design brain" of the pipeline, using a **multi-agent collaboration architecture**:

管線的「教學設計大腦」，採用**多智能體協作架構**：

1. **Subject Classification / 學科分類** — Auto-classifies the course requirement into Physics, Biology, Mathematics, or Computer Science to load subject-specific system prompts. / 自動判斷課程需求屬於物理、生物、數學或電腦科學，載入對應的學科專屬系統提示詞。
2. **Student Background Analysis / 學生背景分析** — LLM interprets the student persona to infer prior knowledge, knowledge gaps, and required teaching adjustments. / LLM 解析學生人物誌，推斷先備知識、知識缺口與所需教學調整。
3. **Draft Generation / 初稿生成** — Produces a structured lesson blueprint (JSON) with per-slide titles, bullet content, speaker notes, slide types, and cross-slide context. / 生成結構化課程藍圖（JSON），包含每張投影片的標題、條列內容、講稿、類型與跨頁上下文。
4. **Multi-Agent Reflection Loop / 多智能體反思迴圈**：
   - **SlideAudit** — Checks each slide for pedagogical completeness / 檢查每張投影片的教學完整性
   - **FeedbackTool (Student Simulator) / 學生模擬器** — Reads the draft from the target student's perspective, flagging comprehension gaps / 以目標學生視角閱讀草稿，標記理解障礙
   - **FineTuningTool** — Revises slides based on feedback / 根據回饋修正投影片內容
5. **Final Script Generation / 最終稿生成** — After multiple refinement iterations, produces the final structured blueprint. / 經多輪迭代後產出最終結構化藍圖。
6. **Math Validation / 數學驗證** — For math/physics subjects, the LLM generates executable Python verification code that is actually run to confirm formula and calculation correctness. / 對數學/物理科目，LLM 生成可執行的 Python 驗證程式碼並實際執行，確認公式與計算的正確性。
7. **Concept Supervision / 概念監督** — A factual correctness audit across all subjects: corrects conceptual errors, dimensional inconsistencies, and derivation mistakes. / 對所有科目進行事實正確性審計：修正概念錯誤、維度不一致與推導失誤。

**Output / 輸出**: `data/{request_id}/blueprint.json`

### Stage 2: Adaptation Layer / 適應層改寫

The core of the system's **Adaptive Teaching** capability. Rewrites both `slide_content` (on-screen text) and `speakers_note` (narration) to match the target student's grade level, background knowledge, and cognitive profile.

系統實現 **「適應性教學」** 的核心。根據學生人物誌的年級水準、先備知識與認知特徵，改寫每張投影片的螢幕文字與講稿。

**Grade-Level Calibration / 年級校準規則**：

| Level / 年級 | Strategy / 策略 |
|---|---|
| Elementary / Middle School / 小學/國中 | Short sentences, concrete language, one idea at a time, immediate term definitions, intuitive analogies / 短句、具體語言、一次一個概念、即時定義術語、直覺類比 |
| High School / 高中 | Preserve core academic terminology, concise explanations, explicit reasoning, avoid unnecessary formalism / 保留核心學術術語、簡潔解釋、顯性推理、避免不必要的形式化 |
| Undergraduate / 大學 | Preserve technical vocabulary, maintain rigor and abstraction, simplify only wording not concepts / 保留技術詞彙、維持嚴謹性與抽象度、僅簡化措辭而非概念 |

**Hard Rules / 強制規則**：
- First-use definition: every jargon term must be defined at its first occurrence / 首次出現的術語必須當場定義
- Preserve all LaTeX math expressions exactly / 保留所有 LaTeX 數學表達式
- Never remove core reasoning steps / 不得刪除核心推理步驟
- Never distort scientific facts for simplicity / 不得為簡化而扭曲科學事實

**Output / 輸出**: `data/{request_id}/blueprint_adapted.json`

### Stage 3: Slide Image Generation / 投影片圖像生成

Renders each adapted slide as a high-quality PNG image using a template-based approach with OpenAI `gpt-image-2`.

使用 OpenAI `gpt-image-2` 模型，以模板為基礎將每張改寫後的投影片渲染為高品質 PNG 圖像。

1. **Visual Style Pipeline / 視覺風格管線** — Determines a cohesive visual style (color palette, font conventions, diagram aesthetics) from the course requirement and student persona. / 根據課程需求與學生人物誌決定統一的色彩、字體與圖表美學風格。
2. **Image Prompt Pipeline / 圖像提示詞管線** — Classifies each slide into text-only, diagram, or mixed layout and generates a corresponding rendering prompt. / 將每張投影片分類為純文字、圖表或混合佈局，生成對應的渲染提示詞。
3. **Image Generation / 圖像生成** — Uses `gpt-image-2` to render each slide onto `layout_template.png`. Up to 4 slides processed concurrently. / 以 `layout_template.png` 為底板渲染每張投影片，最多 4 張並行處理。
4. **Math Image Validation / 數學圖像驗證** — For math/physics subjects, validates rendered formulas and diagrams; flawed slides trigger an auto-fix loop (matplotlib regeneration + general image repair), up to 3 retries. / 對數學/物理科目驗證圖像中公式與圖表的正確性，不合格者自動觸發修正迴圈（最多重試 3 次）。

**Output / 輸出**: `data/{request_id}/image/slide_N_image.png`

### Stage 4: TTS Audio Generation / 語音合成

Converts each slide's `speakers_note` into spoken audio using OpenAI `gpt-4o-mini-tts`.

使用 OpenAI `gpt-4o-mini-tts` 模型將每張投影片的講稿轉換為語音。

1. **Voice Profile Generation / 聲音人物誌生成** — LLM analyzes the student persona and course requirement to produce a detailed voice specification covering accent, tone, pacing, prosody, enthusiasm, emotion, and pronunciation style. / LLM 分析學生人物誌與課程需求，產出詳細的聲音規格（口音、語調、節奏、韻律、熱情度、情感、發音風格）。
2. **Audio Synthesis / 音訊合成** — Generates an `.mp3` audio clip per slide using the `marin` voice calibrated to the profile. Up to 4 slides processed concurrently. / 以 `marin` 聲線為基礎，根據聲音規格為每張投影片生成 MP3 音檔，最多 4 段並行處理。

**Output / 輸出**: `data/{request_id}/audio/slide_N_audio.mp3`

### Stage 5: Video Assembly / 影片組裝

Uses `moviepy` to pair each slide image with its audio track, insert buffer frames between slides, and concatenate into a single `.mp4` file.

使用 `moviepy` 將每張投影片圖像與對應音檔配對，投影片之間插入緩衝幀，串接為單一 MP4 檔案。

- **Resolution / 解析度**: 1080p
- **Frame rate / 幀率**: 24 fps
- **Video codec / 視訊編碼**: H.264
- **Audio codec / 音訊編碼**: AAC
- **Buffer between slides / 投影片間緩衝**: 0.5s

**Output / 輸出**: `data/{request_id}/video/final_presentation_{request_id}.mp4`

---

## Pedagogical Design / 教學設計

TeachingMonster is built for the **1st AI Teaching Challenge**, targeting three core dimensions:

TeachingMonster 為 **第一屆 AI 教學挑戰賽** 設計，對應三大核心維度：

| Competition Dimension / 競賽維度 | TeachingMonster Approach / 對應設計 |
|---|---|
| **Knowledge Scaffolding / 知識鷹架** | Background analysis infers prior knowledge & gaps; adaptation layer builds conceptual bridges by grade level; multi-agent reflection loop ensures complete logical deconstruction / 背景分析推斷先備知識與缺口；適應層根據年級水準搭建概念橋樑；多智能體反思迴圈確保邏輯解構完整 |
| **Adaptive Teaching / 適應性教學** | Student-persona-driven adaptation (vocabulary, sentence complexity, pacing, scaffolding depth); grade-level calibration from elementary through undergraduate; student simulator detects comprehension gaps from the learner's perspective / 學生人物誌驅動的適應層改寫（詞彙、句式、節奏、鷹架深度）；年級校準規則涵蓋小學至大學；學生模擬器從學習者視角檢測理解障礙 |
| **Cognitive Engagement / 認知參與維持** | Diverse slide types (base, concept_check, puzzle, algorithm walkthrough); voice-profile-driven emotional calibration; unified visual style to reduce cognitive load / 多樣化投影片類型（基礎、概念檢查、謎題、演算法逐步解說）；聲音人物誌驅動的語音情感校準；視覺風格統一以降低認知負荷 |

### Slide Types / 投影片類型

| Type / 類型 | Purpose / 用途 |
|---|---|
| `base` | Standard content slide with title, bullets, and narration / 標準內容投影片 |
| `concept_check` | Conceptual question testing understanding, with expected reasoning and correct insight / 概念檢查題，附預期推理過程與正確洞見 |
| `puzzle` | Curiosity-inducing question with hint and learning purpose / 引發好奇心的謎題，附提示與學習目的 |
| `algorithm` | Step-by-step algorithm walkthrough with visualization and key insight / 演算法逐步解說，附視覺化描述與關鍵洞見 |

---

## Third-Party API Services / 第三方 API 服務

The system relies on the following external services. All API keys are managed via `config/credentials.ini`.

系統依賴以下外部服務，所有 API 金鑰透過 `config/credentials.ini` 統一管理。

### Required / 必要

| Service / 服務 | Purpose / 用途 | Environment Variable / 環境變數 |
|---|---|---|
| **OpenAI** | GPT models (text generation), gpt-image-2 (slide rendering), gpt-4o-mini-tts (voice synthesis) / GPT 模型（文字生成）、gpt-image-2（投影片渲染）、gpt-4o-mini-tts（語音合成） | `OPENAI_API_KEY` |
| **AWS S3** | Cloud storage for generated videos; presigned URL generation / 雲端儲存生成影片與預簽名 URL | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME` |

### Optional / 可選（DEV mode / DEV 模式使用）

| Service / 服務 | Purpose / 用途 | Environment Variable / 環境變數 |
|---|---|---|
| **Ollama** | Self-hosted or cloud LLMs (DeepSeek-V3.1, GPT-OSS, Qwen3.5) for DEV mode / 自託管或雲端 LLM，用於 DEV 模式 | `OLLAMA_API_KEY` |
| **Cohere** | Reranking and embedding services (via llama-index) / 重排序與嵌入服務（透過 llama-index） | `COHERE_API_KEY` |
| **HuggingFace** | Model hub for sentence-transformers and transformers / 模型庫（sentence-transformers、transformers） | `HuggingFace_API_KEY` |

### Credentials File Format / 憑證檔格式

Create `config/credentials.ini` with the following structure:

建立 `config/credentials.ini`，結構如下：

```ini
[openai]
api_key = sk-your-openai-api-key

[ollama]
api_key = your-ollama-api-key

[cohere]
api_key = your-cohere-api-key

[HuggingFace_API_KEY]
api_key = hf-your-huggingface-api-key

[aws_access_key_id]
api_key = YOUR_AWS_ACCESS_KEY_ID

[aws_secret_access_key]
api_key = YOUR_AWS_SECRET_ACCESS_KEY
```

---

## API Reference / API 參考

### `POST /v1/{env}/video/generate`

Generate a new educational video. `{env}` is either `dev` (Ollama-hosted models) or `prod` (OpenAI models).

生成新的教學影片。`{env}` 為 `dev`（Ollama 模型）或 `prod`（OpenAI 模型）。

**Request Body / 請求體**:
```json
{
  "request_id": "unique-request-identifier",
  "course_requirement": "Description of the course topic and learning goals",
  "student_persona": "Description of the target student's grade level and background"
}
```

**Response / 回應**:
```json
{
  "video_url": "https://s3.amazonaws.com/.../final_presentation_xxx.mp4?...",
  "subtitle_url": null,
  "supplementary_url": null
}
```

### `POST /v1/files/{request_id}/video`

Retrieve the S3 URL for a previously generated video (does not re-run the pipeline).

取回已生成影片的 S3 URL（不重新執行管線）。

### Dry-Run Mode / 乾跑模式

Pass the `X-Dry-Run: true` header to receive a dummy response without executing the pipeline:

傳入 `X-Dry-Run: true` 標頭即可獲得模擬回應，不執行管線：

```bash
curl -X POST "http://localhost:8000/v1/dev/video/generate" \
     -H "Content-Type: application/json" \
     -H "X-Dry-Run: true" \
     -d '{"request_id":"test","course_requirement":"...","student_persona":"..."}'
```

---

## Setup & Deployment / 環境安裝與部署

### Prerequisites / 前置需求

- **Python** 3.10+
- **FFmpeg** (required by `moviepy` for video rendering / `moviepy` 影片渲染所需)
- **NVIDIA GPU** (recommended for local LLM inference / 建議用於本地 LLM 推論)

### Option A: Conda Environment / 方案 A：Conda 環境

```bash
# Create and activate a conda environment / 建立並啟用 conda 環境
conda create -n teachingmonster python=3.10 -y
conda activate teachingmonster

# Install dependencies from requirements.txt / 從 requirements.txt 安裝依賴
pip install -r requirements.txt
```

### Option B: venv (Standard Python) / 方案 B：venv（標準 Python）

```bash
# Create and activate a virtual environment / 建立並啟用虛擬環境
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Install dependencies / 安裝依賴
pip install -r requirements.txt
```

### Environment Variables / 環境變數

| Variable / 變數 | Required / 必要 | Purpose / 用途 |
|---|---|---|
| `env` | Always / 必要 | `DEV` (Ollama models) or `PROD` (OpenAI models) / 選擇模型環境 |
| `OPENAI_API_KEY` | PROD mode / PROD 模式 | OpenAI API key for GPT, image, and TTS models / OpenAI API 金鑰 |
| `AWS_ACCESS_KEY_ID` | Always / 必要 | S3 upload credentials / S3 上傳憑證 |
| `AWS_SECRET_ACCESS_KEY` | Always / 必要 | S3 upload credentials / S3 上傳憑證 |
| `AWS_REGION` | Always / 必要 | S3 bucket region (default: `eu-central-1`) / S3 儲存桶區域 |
| `S3_BUCKET_NAME` | Always / 必要 | Target S3 bucket (default: `ling-ml-bucket`) / 目標 S3 儲存桶 |

### Launching / 啟動

```bash
# Set environment and start the server / 設定環境並啟動伺服器
$env:env = "PROD"   # Windows PowerShell
export env=PROD      # Linux / macOS

python service/api.py
```

Server starts at `http://0.0.0.0:8000`. / 伺服器啟動於 `http://0.0.0.0:8000`。

---

## Exposing the Service / 公開服務

Since the server runs on `localhost:8000`, it is only accessible on your local machine. To expose the API publicly, use **Cloudflare Tunnel (`cloudflared`)**.

伺服器預設僅限本機存取。如需公開 API，可使用 **Cloudflare Tunnel (`cloudflared`)**。

### 1. Install cloudflared / 安裝 cloudflared

Download from [Cloudflare](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-run/).

### 2. Start the Tunnel / 啟動隧道

```bash
cloudflared tunnel --url http://localhost:8000
```

### 3. Get your Public URL / 取得公開 URL

Cloudflare provides a temporary forwarding address:

```text
https://your-random-id.trycloudflare.com -> http://localhost:8000
```

Use this `https` URL as the base for all API requests:

```bash
curl -X POST "https://your-random-id.trycloudflare.com/v1/prod/video/generate" \
     -H "Content-Type: application/json" \
     -d '{"request_id":"req_001","course_requirement":"...","student_persona":"..."}'
```

---

## Data Flow / 資料流

```text
POST /v1/{env}/video/generate
  |  { request_id, course_requirement, student_persona }
  v
VideoWorker.process_request()
  |  Saves input.json to data/{request_id}/
  |  Calls run_pipeline() via asyncio.to_thread()
  v
run.py:main()
  |
  |-- Stage 1: blueprint.run()
  |     LLM generates structured lesson -> data/{request_id}/blueprint.json
  |
  |-- Stage 2: adaptation.run()
  |     LLM adapts to student persona -> data/{request_id}/blueprint_adapted.json
  |
  |-- Stage 3: slide.run()
  |     Visual style analysis -> gpt-image-2 renders each slide -> data/{request_id}/image/*.png
  |
  |-- Stage 4: tts.run()
  |     Voice profile + audio synthesis -> data/{request_id}/audio/*.mp3
  |
  |-- Stage 5: video_gen.run()
  |     moviepy concatenates images + audio -> data/{request_id}/video/final_presentation_{id}.mp4
  |
  v
CloudStorage.upload_file()
  |  Uploads to S3, generates presigned URL (48h expiry)
  v
Response: { video_url: "https://s3..." }
```

---

## Project Structure / 專案結構

```text
TeachingMonster/
├── config/
│   └── credentials.ini          # API keys (git-ignored) / API 金鑰（不入版控）
├── data/                         # Per-request output directory / 每次請求的輸出目錄
│   └── {request_id}/
│       ├── input.json
│       ├── blueprint.json
│       ├── blueprint_adapted.json
│       ├── draft/                # Iteration drafts / 迭代草稿
│       ├── image/                # slide_N_image.png
│       ├── audio/                # slide_N_audio.mp3
│       └── video/                # final_presentation_{id}.mp4
├── logs/
├── readme_image/                # Documentation images / 文件圖片
├── service/
│   ├── api.py                   # FastAPI server / FastAPI 伺服器
│   ├── worker.py                # Background pipeline executor / 背景管線執行器
│   └── storage.py               # AWS S3 upload / AWS S3 上傳
├── src/
│   ├── io/
│   │   └── path_definition.py   # Project path resolver / 專案路徑解析
│   ├── logic/
│   │   ├── __init__.py          # build_standard_chat_prompt_template()
│   │   └── writers/
│   │       ├── blueprint/       # Stage 1: Lesson blueprint generation / 課程藍圖生成
│   │       │   ├── run.py
│   │       │   ├── generation_pipeline.py
│   │       │   ├── structured_output.py
│   │       │   ├── subject_classifier.py
│   │       │   ├── system_prompt/     # Subject-specific prompts / 學科專屬提示詞
│   │       │   ├── background_system_prompt/
│   │       │   ├── decompress_prompt/
│   │       │   ├── agent/             # Multi-agent tools / 多智能體工具
│   │       │   └── post_processing/   # Math validation & concept supervision
│   │       ├── adaptation/      # Stage 2: Persona-aware adaptation / 適應層改寫
│   │       │   └── run.py
│   │       ├── slide/           # Stage 3: Slide image rendering / 投影片圖像生成
│   │       │   ├── run.py
│   │       │   ├── render_prompt.py
│   │       │   ├── image_validation.py
│   │       │   ├── visual_style/
│   │       │   ├── image_logic/
│   │       │   └── image_matplotlib/
│   │       ├── tts/             # Stage 4: TTS audio synthesis / 語音合成
│   │       │   ├── run.py
│   │       │   ├── generation_pipeline.py
│   │       │   └── structured_output.py
│   │       └── video_gen/       # Stage 5: Video assembly / 影片組裝
│   │           └── run.py
│   └── ollama_connection.py
├── layout_template.png          # Slide background template / 投影片底板模板
├── model_orchestration.py       # DEV/PROD model registry / 模型配置註冊表
├── initialization.py            # Credential loader / 憑證載入器
├── run.py                       # Master pipeline orchestrator / 主管線編排器
├── run_flask.py                 # Flask alternative entry point / Flask 替代入口
├── request_simulation.py        # Test request simulator / 測試請求模擬器
├── requirements.txt             # Python dependencies / Python 依賴
└── README.md
```

---

## Core Dependencies / 核心依賴

| Package / 套件 | Version / 版本 | Purpose / 用途 |
|---|---|---|
| `fastapi` | 0.135 | Web framework / Web 框架 |
| `uvicorn` | 0.41 | ASGI server / ASGI 伺服器 |
| `openai` | 2.28 | OpenAI SDK (GPT, image, TTS) / OpenAI SDK |
| `langchain` | 1.2 | LLM orchestration framework / LLM 編排框架 |
| `langchain-openai` | 1.0 | LangChain OpenAI integration / LangChain OpenAI 整合 |
| `langchain-ollama` | 1.0 | LangChain Ollama integration / LangChain Ollama 整合 |
| `llama-index` | 0.14 | Data framework for LLM applications / LLM 應用資料框架 |
| `moviepy` | 2.2 | Video assembly from images + audio / 圖像與音訊組裝為影片 |
| `boto3` | 1.42 | AWS S3 upload and presigned URLs / AWS S3 上傳與預簽名 URL |
| `pydantic` | 2.12 | Data validation and structured output parsing / 資料驗證與結構化輸出解析 |
| `matplotlib` | 3.10 | Programmatic diagram rendering / 程式化圖表渲染 |
| `mutagen` | 1.47 | MP3 audio duration detection / MP3 音訊長度偵測 |
| `aiofiles` | 25.1 | Async file I/O / 非同步檔案讀寫 |

---

## License / 授權

This project is developed for the **1st AI Teaching Challenge (Teaching Monster Challenge)**.

本專案為 **第一屆 AI 教學挑戰賽（Teaching Monster Challenge）** 參賽作品。
