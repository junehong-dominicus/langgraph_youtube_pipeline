# Product Requirements Document (PRD)

## Product Name
Automated Weekly YouTube Content Pipeline (LangGraph-based)

---

## 1. Overview

This product is an automated system that plans, generates, produces, and uploads YouTube videos on a weekly basis based on a predefined topic or topic strategy. The system is built using **LangGraph** to orchestrate multiple AI-driven and deterministic steps such as scripting, asset generation, video composition, and YouTube upload.

The primary goal is to minimize human intervention while maintaining content quality, reliability, and extensibility.

---

## 2. Goals & Objectives

### Primary Goals
- Automatically publish **one YouTube video per week**
- Ensure reliability through stateful orchestration
- Enable easy extension (Shorts, multi-language, analytics)

### Success Metrics
- Successful weekly uploads without manual intervention
- < 5% pipeline failure rate
- Average video generation time < 15 minutes

---

## 3. Target Users

### Primary Users
- Indie creators
- Developers running faceless YouTube channels
- AI automation enthusiasts

### Secondary Users
- Marketing teams
- Educational content creators

---

## 4. Functional Requirements

### 4.1 Scheduling
- The system **must run automatically once per week**
- Supported platforms:
  - Windows (Task Scheduler)
  - macOS (launchd, optimized for Mac mini)

### 4.2 Topic Management
- Accept a predefined topic OR
- Select a topic from a predefined list
- Future extension: trend-based topic selection

### 4.3 Script Generation
- Generate a 3–5 minute YouTube-ready script
- Script structure:
  - Hook / Introduction
  - Main content
  - Closing / CTA
- Language: English (default)

### 4.4 Voice Generation (TTS)
- Convert script to natural-sounding speech
- Output format: MP3 or WAV
- Voice style configurable

### 4.5 Visual Asset Generation
- Generate or fetch visual assets:
  - AI-generated images OR
  - Stock images/videos
- Assets must align with script sections

### 4.6 Video Composition
- Combine images/videos with voiceover
- Add basic transitions
- Output format: MP4 (YouTube-compatible)

### 4.7 Metadata Generation
- Automatically generate:
  - Title
  - Description
  - Tags
- SEO-optimized for YouTube

### 4.8 YouTube Upload
- Upload video via YouTube Data API v3
- Set metadata during upload
- Default visibility: Public

---

## 5. Non-Functional Requirements

### 5.1 Reliability
- Each step must be stateful
- Failures must be resumable from the last successful node

### 5.2 Observability
- Log output and errors to files
- Track final upload status

### 5.3 Performance
- End-to-end pipeline should complete within 30 minutes

### 5.4 Security
- API keys stored in environment variables
- OAuth tokens securely stored

---

## 6. System Architecture

### 6.1 High-Level Flow

```
Scheduler → LangGraph Entry
         → Topic Planner
         → Script Generator
         → TTS Generator
         → Asset Generator
         → Video Composer
         → Metadata Generator
         → YouTube Upload
         → END
```

### 6.2 Orchestration
- LangGraph used as the state machine
- Typed state object passed between nodes

---

## 7. Tech Stack

### Core
- Python 3.10+
- LangGraph
- LangChain

### Media
- MoviePy or FFmpeg
- OpenAI / ElevenLabs (TTS)
- Image generation API (DALL·E, Stable Diffusion)

### Platform
- Windows Task Scheduler
- macOS launchd

### APIs
- YouTube Data API v3

---

## 8. Assumptions & Constraints

- The system runs on an always-on machine (PC or Mac mini)
- YouTube API quota is sufficient for weekly uploads
- No real-time human interaction required

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|----|----|
| API failure | Retry + resumable graph |
| YouTube upload errors | Automatic retry / logging |
| Poor content quality | Prompt tuning & review mode |

---

## 10. LangGraph Node Contracts (Explicit I/O)

This section defines the explicit input and output contracts for each LangGraph node. All nodes operate on a shared, typed state object (`VideoState`) and must only read/write the fields specified below to ensure determinism and resumability.

### 10.1 Shared State Schema

```python
class VideoState(TypedDict):
    topic: str
    script: Optional[str]
    voice_path: Optional[str]
    image_paths: Optional[List[str]]
    video_path: Optional[str]
    title: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    upload_status: Optional[str]
    error: Optional[str]
```

---

### 10.2 Entry Node – Scheduler Trigger

**Purpose**  
Initialize the workflow with a topic and empty derived fields.

**Input**
- External scheduler payload (cron / Task Scheduler / launchd)

**Reads**
- None

**Writes**
- `topic`

**Failure Behavior**
- Abort graph if topic is missing

---

### 10.3 Topic Planner Node

**Purpose**  
Validate or select the topic for the current week.

**Reads**
- `topic`

**Writes**
- `topic` (normalized or replaced)

**Failure Behavior**
- Retry once
- Fallback to default topic

---

### 10.4 Script Generator Node

**Purpose**  
Generate a structured YouTube-ready script.

**Reads**
- `topic`

**Writes**
- `script`

**Output Guarantees**
- 3–5 minute spoken length
- Intro → Body → Outro structure

**Failure Behavior**
- Retry with simplified prompt

---

### 10.5 Voice (TTS) Generator Node

**Purpose**  
Convert script text into a voiceover audio file.

**Reads**
- `script`

**Writes**
- `voice_path`

**Output Guarantees**
- Audio duration matches script length ±5%

**Failure Behavior**
- Retry with alternative voice

---

### 10.6 Visual Asset Generator Node

**Purpose**  
Generate or retrieve visual assets aligned with the script.

**Reads**
- `script`

**Writes**
- `image_paths`

**Output Guarantees**
- Minimum of 3 assets

**Failure Behavior**
- Fallback to stock images

---

### 10.7 Video Composer Node

**Purpose**  
Compose final video from visuals and voiceover.

**Reads**
- `image_paths`
- `voice_path`

**Writes**
- `video_path`

**Output Guarantees**
- MP4 format
- YouTube-compatible resolution and codec

**Failure Behavior**
- Abort and log error

---

### 10.8 Metadata Generator Node

**Purpose**  
Generate SEO-optimized metadata for YouTube.

**Reads**
- `topic`
- `script`

**Writes**
- `title`
- `description`
- `tags`

**Output Guarantees**
- Title ≤ 100 characters
- Description ≥ 2 paragraphs

**Failure Behavior**
- Retry with reduced creativity

---

### 10.9 YouTube Upload Node

**Purpose**  
Upload the video and metadata to YouTube.

**Reads**
- `video_path`
- `title`
- `description`
- `tags`

**Writes**
- `upload_status`

**Output Guarantees**
- Publicly accessible video URL (future extension)

**Failure Behavior**
- Retry (exponential backoff)
- Persist failure state for manual recovery

---

### 10.10 Terminal Node (END)

**Purpose**  
Mark workflow completion.

**Reads**
- `upload_status`

**Writes**
- None

**Success Criteria**
- `upload_status == "success"`

---

## 11. Conditional Edges & Control Flow (Retry / Fallback / Human Approval)

This section defines conditional edges used in the LangGraph to improve reliability, quality control, and operational safety. Conditional routing is based on state inspection after each node execution.

---

### 11.1 Retry Logic (Automatic)

**Purpose**  
Automatically retry transient failures such as API timeouts or generation errors.

**Applicable Nodes**
- Script Generator
- Voice (TTS) Generator
- Metadata Generator
- YouTube Upload

**Condition**
- Exception raised OR required output field is missing

**Routing Logic**

```python
if state.get("error") is not None:
    return "retry"
else:
    return "next"
```

**Policy**
- Max retries: 2
- Retry prompt must be simplified or constrained
- Exponential backoff for external APIs

---

### 11.2 Fallback Logic (Graceful Degradation)

**Purpose**  
Ensure pipeline completion even when optimal generation fails.

**Fallback Examples**

| Primary Node | Fallback Node |
|------------|--------------|
| Topic Planner | Default Topic Selector |
| Script Generator | Template-Based Script |
| Asset Generator | Stock Image Fetcher |
| TTS Generator | Alternate Voice / Provider |

**Condition**
- Retry count exceeded

**Routing Logic**

```python
if retries_exceeded:
    return "fallback"
```

**Guarantee**
- Fallback nodes must be deterministic
- No external LLM calls if possible

---

### 11.3 Human-in-the-Loop Approval (Optional)

**Purpose**  
Allow manual approval before irreversible actions (e.g., YouTube upload).

**Approval Gate Placement**
- After Video Composer
- Before YouTube Upload

**Reads**
- `video_path`
- `title`
- `description`

**Writes**
- `approval_status` (approved / rejected)

**Condition**

```python
if state.get("approval_status") == "approved":
    return "upload"
else:
    return "halt"
```

**Approval Interfaces (Out of Scope, Supported)**
- CLI prompt
- Web dashboard
- Slack / Discord button

---

### 11.4 Quality Gate Conditions

**Purpose**  
Prevent low-quality content from being uploaded automatically.

**Example Conditions**
- Script length < minimum threshold
- Audio duration mismatch
- Video render failure

**Routing Logic**

```python
if not quality_check_passed:
    return "retry_or_fallback"
```

---

### 11.5 Example Conditional Graph Flow

```
Script Generator
   ├── success → TTS Generator
   ├── retry   → Script Generator
   └── fail    → Script Fallback

Video Composer
   ├── approved → YouTube Upload
   └── rejected → END (manual review)
```

---

### 11.6 Operational Guarantees

- No infinite loops
- All retries and fallbacks are logged
- Human approval halts execution safely

---

## 12. Shorts + Long-form Branching Contracts

This section defines explicit branching contracts for generating **YouTube Shorts** and **Long-form videos** within the same LangGraph. Branching is decided early in the workflow and propagated through downstream nodes to ensure format-specific behavior.

---

### 12.1 Branching Decision Node – Content Type Router

**Purpose**  
Decide whether the current execution produces a YouTube Short, a Long-form video, or both.

**Reads**
- `topic`

**Writes**
- `content_type` ("short" | "long" | "both")

**Decision Rules (Initial Version)**
- Default: `long`
- If topic is trend-driven or promotional → `short`
- Future: analytics-based decision

---

### 12.2 Extended Shared State Schema

```python
class VideoState(TypedDict):
    topic: str
    content_type: Literal["short", "long", "both"]
    script: Optional[str]
    short_script: Optional[str]
    voice_path: Optional[str]
    image_paths: Optional[List[str]]
    video_path: Optional[str]
    short_video_path: Optional[str]
    title: Optional[str]
    short_title: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    upload_status: Optional[str]
    short_upload_status: Optional[str]
    error: Optional[str]
```

---

### 12.3 Script Generation Branch

#### Long-form Script Node

**Reads**
- `topic`

**Writes**
- `script`

**Guarantees**
- 3–5 minutes spoken length

---

#### Shorts Script Node

**Reads**
- `topic`

**Writes**
- `short_script`

**Guarantees**
- ≤ 60 seconds
- Strong hook in first 3 seconds

---

### 12.4 Asset & Video Composition Branching

#### Long-form Video Composer

**Reads**
- `script`
- `voice_path`
- `image_paths`

**Writes**
- `video_path`

**Constraints**
- Aspect ratio: 16:9
- Resolution: 1920×1080

---

#### Shorts Video Composer

**Reads**
- `short_script`
- `voice_path` (or regenerated)
- `image_paths`

**Writes**
- `short_video_path`

**Constraints**
- Aspect ratio: 9:16
- Duration ≤ 60 seconds
- Resolution: 1080×1920

---

### 12.5 Metadata Branching

#### Long-form Metadata Node

**Writes**
- `title`
- `description`
- `tags`

---

#### Shorts Metadata Node

**Writes**
- `short_title`
- `tags`

**Constraints**
- Title ≤ 40 characters
- Must include #Shorts hashtag

---

### 12.6 Upload Branching

#### Long-form Upload Node

**Reads**
- `video_path`
- `title`
- `description`

**Writes**
- `upload_status`

---

#### Shorts Upload Node

**Reads**
- `short_video_path`
- `short_title`

**Writes**
- `short_upload_status`

---

### 12.7 Example Branching Flow

```
Content Router
   ├── short → Shorts Pipeline → Shorts Upload → END
   ├── long  → Long Pipeline   → Upload        → END
   └── both  → Parallel Shorts + Long Pipelines → END
```

---

### 12.8 Operational Guarantees

- Shorts and Long-form pipelines are isolated
- Failure in Shorts does not block Long-form upload
- State fields are never overwritten across branches

---

## 13. Future Enhancements

- YouTube Shorts pipeline
- Multi-language video generation
- Performance analytics & feedback loop
- Trend-based topic recommendation
- Human-in-the-loop approval step

---

## 11. Out of Scope

- Live streaming
- Manual video editing UI
- Real-time audience interaction

---

## 12. Approval

This PRD defines the initial scope and requirements for the automated weekly YouTube content pipeline powered by LangGraph.

**Status:** Draft

