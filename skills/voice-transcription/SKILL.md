---
name: voice-transcription
description: Transcribe audio files to text via the Pazi API with automatic credit billing. Use when you receive audio/voice messages or need to transcribe audio files.
metadata:
  {
    "openclaw":
      {
        "emoji": "🎙️",
        "requires": { "bins": ["curl"] },
      },
  }
---

# Voice Transcription (Pazi API)

Transcribe audio to text using OpenAI's `gpt-4o-transcribe` model through the Pazi API. Credits are automatically deducted based on audio duration.

## When to Use

- User sends a voice message or audio file
- User asks you to transcribe audio
- You need to process audio content from any channel (Slack, Telegram, WhatsApp, etc.)

**Note:** For channel-delivered audio (Slack voice messages, Telegram audio, etc.), the `message:transcribed` hook handles transcription and billing automatically — you don't need to call the API manually. This skill is for cases where you need to explicitly transcribe an audio file.

## Endpoints

### POST /transcribe — Transcribe Audio File

Upload an audio file and receive the transcribed text. Credits are deducted before transcription and refunded on failure.

```bash
curl -X POST "$PAZI_API_URL/transcribe" \
  -H "X-Proxy-Token: $PROXY_TOKEN" \
  -F "audio=@/path/to/audio.webm" \
  -F "durationSeconds=30"
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | file | Yes | Audio file (webm, ogg, mp3, m4a, wav, mp4) |
| `durationSeconds` | number | No | Audio duration in seconds. If omitted, estimated from file size |

**Response (200):**
```json
{
  "text": "Transcribed text content here...",
  "creditsDeducted": 2,
  "creditsRemaining": 498
}
```

**Error responses:**
- `400` — Missing audio file
- `402` — Insufficient credits (returns `creditsRequired` and `creditsAvailable`)
- `500` — Transcription failed (credits are automatically refunded)

### POST /transcribe/usage — Report Channel Billing

Report transcription usage for credit deduction. Used by agent extensions when audio is transcribed through channel hooks rather than the upload endpoint.

```bash
curl -X POST "$PAZI_API_URL/transcribe/usage" \
  -H "Content-Type: application/json" \
  -H "X-Proxy-Token: $PROXY_TOKEN" \
  -d '{"durationSeconds": 15}'
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `durationSeconds` | number | Yes | Audio duration in seconds (max 60) |

**Response (200):**
```json
{
  "creditsDeducted": 1,
  "creditsRemaining": 499
}
```

## Credit Pricing

| Duration | Credits | USD Cost |
|----------|---------|----------|
| ≤20s | 1 | ~$0.002 |
| 30s | 2 | ~$0.003 |
| 60s (max) | 3 | ~$0.006 |

- **Rate:** $0.006/minute (gpt-4o-transcribe)
- **Conversion:** 500 credits = $1.00
- **Minimum charge:** 1 credit per request
- **Maximum duration:** 60 seconds per request

## Supported Audio Formats

webm, ogg, mp3, m4a, wav, mp4

## Automatic Channel Billing

When audio arrives through messaging channels (Slack, Telegram, etc.), the `pazi-transcription-billing` extension hook automatically:
1. Detects the `message:transcribed` event
2. Determines audio duration via `ffprobe` (or estimates from file size)
3. Posts usage to `POST /transcribe/usage` for credit deduction

This is best-effort and non-blocking — billing failures never prevent message delivery.
