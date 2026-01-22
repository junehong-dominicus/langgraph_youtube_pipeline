# Automated Weekly YouTube Content Pipeline

An automated system built with **LangGraph** that plans, generates, produces, and uploads YouTube videos (Long-form and Shorts) based on a topic strategy.

## Overview

This project orchestrates a stateful workflow using LangGraph to minimize human intervention in content creation. It handles the entire pipeline from topic selection to YouTube upload, ensuring reliability through structured state management.

## Features

- **Automated Workflow**: Designed to run weekly for consistent publishing.
- **Dual Mode**: Supports Long-form videos, YouTube Shorts, or both simultaneously.
- **AI-Driven Content Creation**:
  - **Scripting**: Generates structured scripts (Hook, Body, CTA).
  - **Voice**: Text-to-Speech (TTS) integration.
  - **Visuals**: Asset generation and retrieval.
  - **Metadata**: SEO-optimized titles, descriptions, and tags.
- **Resumable Architecture**: Stateful execution allows for retries and error handling at specific nodes.

## Architecture

The system uses a graph-based architecture where a typed `VideoState` is passed between nodes:

1.  **Topic Planner**: Selects or validates the topic.
2.  **Content Router**: Determines content type (Short, Long, Both).
3.  **Generators**: Parallel execution for Script, Voice, and Assets.
4.  **Composer**: Assembles media assets into final MP4 video.
5.  **Uploader**: Uploads to YouTube via Data API v3.

## Prerequisites

- Python 3.10+
- FFmpeg (required for MoviePy)
- YouTube Data API credentials

## Installation

1.  Clone the repository.
2.  **Note**: Rename the directory to `langgraph_youtube_pipeline` if it contains hyphens (e.g., `langgraph-youtube-pipeline`), as Python modules cannot contain hyphens.
3.  Create a virtual environment:

```bash
uv venv
```

4.  Install dependencies:

```bash
uv pip install -r requirements.txt
```

## Configuration

Ensure you have the necessary API keys set up in your environment:

- `OPENAI_API_KEY`: For script and metadata generation.
- `GOOGLE_API_KEY` / OAuth Credentials: For YouTube upload.

## Usage

To run the pipeline, execute the module from the root directory:

```bash
python -m langgraph_youtube_pipeline.main
```

## Project Structure

- `state.py`: Defines the `VideoState` schema.
- `nodes.py`: Implementation of logic nodes (Script, Voice, Upload, etc.).
- `graph.py`: LangGraph definition, wiring nodes and conditional edges.
- `main.py`: Entry point to trigger the workflow.