---
name: listenhub-tts
description: >
  使用 ListenHub API 将文本转换为语音（TTS）。支持三种模式：快速合成（/v1/tts）、
  多角色脚本（/v1/speech）、长文本流式合成（/v1/flow-speech/episodes）。
  音色未指定时自动获取音色列表供用户选择，默认使用 chat-girl-105-cn（晓曼）。
  Use when user says: "tts", "text to speech", "语音合成", "文字转语音", "朗读",
  "生成语音", "生成音频", "转音频", "text to audio"
# 只可能被手敲的人用工具：不进模型目录，省下每个会话与每个子代理的固定成本。
disable-model-invocation: true
metadata:
  trigger: TTS语音合成、text to speech、文字转语音、朗读文本、生成音频
---

# ListenHub TTS: 文本转语音

使用 ListenHub OpenAPI 将文本转换为语音。支持三种合成模式，覆盖从短文本到长文本的全场景。

## API 信息

- **Base URL:** `https://api.marswave.ai/openapi`
- **认证:** `Authorization: Bearer $LISTENHUB_API_KEY`（从环境变量读取）
- **前置检查:** 调用任何 API 前先确认 `LISTENHUB_API_KEY` 环境变量已设置，未设置则提示用户配置

## 音色选择流程

### 用户已明确指定音色

直接使用用户指定的 speakerId，跳过选择流程。

### 用户未指定音色

1. 调用 `GET /v1/speakers/list?language=zh` 获取可用音色列表（请求参数与响应字段见 `references/speakers.md`）
2. 按 AskUserQuestion 展示音色列表供用户选择，格式如下：
   - 默认选中 `chat-girl-105-cn`（晓曼 dxqqq）
   - 列表展示：`{name}（{gender}，{speakerId}）`
   - 附带每个音色的 demoAudioUrl 供参考
3. 用户确认后使用选定的 speakerId

### 默认音色

| 字段 | 值 |
|------|-----|
| speakerId | `chat-girl-105-cn` |
| 名称 | 晓曼 dxqqq |

## 三种合成模式

三种模式一次只走一条；**选定模式后先读 `references/modes.md`（端点、参数表、curl 示例、响应与轮询、端到端示例都在其中），再按其中说明调用 API**。

- **模式一 `POST /v1/tts`（快速合成）：** 短文本（< 1000 字）、单音色、要求低延迟。
- **模式二 `POST /v1/speech`（多角色脚本）：** 多角色对话、播客、有声书片段，多个音色交替朗读。
- **模式三 `POST /v1/flow-speech/episodes`（长文本流式）：** 长文本（> 1000 字）、文章朗读，需要 AI 润色或分段处理，也可接收内容 URL。

## 模式选择逻辑

根据用户输入自动选择最合适的模式：

| 条件 | 模式 |
|------|------|
| 文本 ≤ 1000 字，单音色 | 模式一：`/v1/tts` |
| 多角色脚本，需要不同音色 | 模式二：`/v1/speech` |
| 文本 > 1000 字，或需要 AI 润色 | 模式三：`/v1/flow-speech/episodes` |
| 用户提供 URL 作为内容来源 | 模式三：`/v1/flow-speech/episodes` |

如果用户明确指定模式，优先使用用户指定的模式。

## 用户交互

### 音色选择

当用户未指定音色时，使用 AskUserQuestion 展示音色列表：

```
请选择音色（默认：晓曼 dxqqq）：
A. 晓曼 dxqqq（女，chat-girl-105-cn）[默认]
B. [其他音色名称]（[性别]，[speakerId]）
C. ...
```

### 合成参数

可选询问：
- 语速 speed（默认 1.0）
- 输出格式 format（默认 mp3）
- 长文本模式：direct 还是 aiPolish（默认 direct）
- 输出文件路径（默认 `./output.mp3`）

## 输出

1. 将音频保存到指定路径（默认 `./output.mp3`）
2. 输出合成摘要：
   - 使用的模式
   - 音色名称和 ID
   - 音频时长
   - 文件大小
   - 文件路径

## 错误处理

- **401 Unauthorized:** 提示用户检查 `LISTENHUB_API_KEY` 环境变量
- **400 Bad Request:** 检查请求参数，向用户报告具体错误
- **flow-speech failed:** 报告 errorMessage，建议用户重试或切换模式
- **网络错误:** 提示检查网络连接，建议重试
