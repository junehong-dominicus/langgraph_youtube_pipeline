---
title: "Building an Automated YouTube Content Pipeline with LangGraph"
description: "A deep dive into building an end-to-end automated content generation pipeline that plans, generates, produces, and uploads YouTube videos using LangGraph."
date: 2026-01-20
author: June Hong
tags: [LangGraph, YouTube Automation, Python, AI Engineering, FFmpeg]
---

## Introduction

Creating high-quality video content consistently is a challenge. Between scripting, recording voiceovers, sourcing visuals, editing, and managing metadata, a single YouTube video can take hours or even days to complete.

To solve this, I built the **Automated Weekly YouTube Content Pipeline**—an intelligent system designed to plan, generate, produce, and upload YouTube videos (both Long-form and Shorts) with minimal human intervention. Unlike simple script generation tools, this project leverages **LangGraph** for stateful orchestration to handle the entire production lifecycle.

In this post, I'll break down the architecture and key components of this autonomous publishing system.

---

## The Architecture: Orchestrating the Studio

The core of the system is built on **LangGraph**, which allows us to define a graph-based workflow where a typed `VideoState` is passed between nodes. This ensures reliability and allows for complex logic like branching for different content types.

Here is the high-level flow:

1.  **Topic Planner**: Selects or validates the topic for the week.
2.  **Content Router**: Determines if the content should be a Short, Long-form video, or both.
3.  **Generators**: Parallel execution of specialized tasks:
    *   **Scripting**: Generates structured scripts (Hook, Body, CTA).
    *   **Voice**: Converts text to speech using TTS integration.
    *   **Visuals**: Generates or retrieves assets aligned with script sections.
4.  **Composer**: Assembles media assets and voiceovers into a final MP4 video using MoviePy/FFmpeg.
5.  **Metadata Generator**: Creates SEO-optimized titles, descriptions, and tags.
6.  **Uploader**: Uploads the final video to YouTube via the Data API v3.

---

## Key Features

### 1. Dual Mode Support

The pipeline isn't limited to one format. It intelligently routes content creation to support **Long-form videos**, **YouTube Shorts**, or both simultaneously. This allows for a comprehensive content strategy that leverages the discoverability of Shorts and the depth of long-form content.

### 2. AI-Driven Content Creation

The system acts as a full production team:
*   **Scriptwriter**: Crafts engaging scripts with proper structure.
*   **Voice Actor**: Generates natural-sounding voiceovers.
*   **Visual Artist**: Creates or fetches relevant imagery.
*   **SEO Specialist**: Optimizes metadata for search rankings.

### 3. Resumable Architecture

One of the biggest challenges in automation is handling failures. By using LangGraph's stateful execution, the pipeline is **resumable**. If an API call fails or a render crashes, the system can retry specific nodes or resume from the last successful state without restarting the entire process.

---

## Tech Stack

*   **LangGraph**: For building the stateful, graph-based application.
*   **Python 3.10+**: The core programming language.
*   **MoviePy / FFmpeg**: For programmatic video editing and composition.
*   **YouTube Data API v3**: For automated uploading and metadata management.
*   **OpenAI**: For script generation and metadata optimization.

---

## Conclusion

The Automated YouTube Content Pipeline demonstrates that AI can be more than just a helper—it can be a comprehensive production engine. By combining generative AI for content creation with LangGraph for robust orchestration, we can automate the labor-intensive parts of video production while maintaining consistency and quality.
