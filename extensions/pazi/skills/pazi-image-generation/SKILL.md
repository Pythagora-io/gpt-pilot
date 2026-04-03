---
name: pazi-image-generation
description: How to generate images using the image_generate tool via Pazi's image generation service.
metadata: { "openclaw": { "emoji": "🎨" } }
---

# Image Generation

Generate images using the `image_generate` tool powered by GPT Image 1.5.

## When to Use

- **Only generate images when the user explicitly asks** for an image, illustration, visual, picture, graphic, or similar
- Do NOT spontaneously generate images — wait for a clear request
- If unsure whether the user wants an image, ask first

## How to Generate

Use the `image_generate` tool with a descriptive `prompt`:

```
image_generate(prompt="A serene mountain landscape at sunset with a calm lake reflection")
```

## Prompt Guidelines

- Be specific and descriptive — detail matters for quality
- Describe colors, lighting, composition, and style when relevant
- Include the subject, setting, mood, and any specific artistic style
- For text in images: specify exact text clearly in quotes

## Quality & Size

- **Default quality**: `medium` — good balance of cost and quality
- **High quality**: Only suggest when user explicitly asks for highest quality or for print-ready images
- **Low quality**: For quick drafts or when user wants to minimize cost
- **Default size**: `1024x1024` (square)
- **Landscape**: `1536x1024` — for wide scenes, landscapes
- **Portrait**: `1024x1536` — for tall subjects, portraits

## After Generation

- Briefly describe what was generated
- The image is automatically delivered to the user's channel (webchat, Slack, Telegram)
- Image generation costs credits — mention this if the user asks about costs

## Error Handling

- If generation fails due to content policy, explain that the prompt was flagged and suggest rephrasing
- If generation fails due to insufficient credits, inform the user they need to add credits
- If generation times out, suggest trying again
