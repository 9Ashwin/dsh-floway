# ListenHub TTS 音色列表查询

本文档是 `SKILL.md` 的下沉细节，内容自 `SKILL.md` 原样搬运、未作改写。
仅在「用户未指定音色」这条路径下读取，用于渲染音色选择列表。

## 音色列表查询

**接口：** `GET /v1/speakers/list`

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| language | string | 否 | 筛选语言，如 `zh`（中文）、`en`（英文） |

**响应：**

```json
{
  "speakers": [
    {
      "name": "晓曼 dxqqq",
      "speakerId": "chat-girl-105-cn",
      "demoAudioUrl": "https://cdn.example.com/demo.mp3",
      "gender": "female",
      "language": "zh"
    }
  ]
}
```
