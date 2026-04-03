import http from "node:http";
import https from "node:https";
import type { ImageGenerationProvider } from "openclaw/plugin-sdk/image-generation";
import { resolvePaziBillingConfig } from "../config.js";
import { getProxyContext, markProxyActivity } from "../context.js";

const PAZI_IMAGE_MODEL = "gpt-image-1.5";
const PAZI_PROVIDER_ID = "pazi";
const DEFAULT_IMAGE_REQUEST_TIMEOUT_MS = 70_000;

const SUPPORTED_SIZES = ["1024x1024", "1024x1536", "1536x1024"] as const;

/** Resolve the image size from request params */
function mapSize(raw: string | undefined): string {
  const normalized = raw?.trim();
  if (normalized && SUPPORTED_SIZES.includes(normalized as (typeof SUPPORTED_SIZES)[number])) {
    return normalized;
  }
  return "1024x1024";
}

type ApiResponse = {
  imageId?: string;
  b64_json?: string;
  s3Url?: string;
  costUsd?: number;
  creditsDeducted?: number;
  quality?: string;
  size?: string;
  revisedPrompt?: string;
  error?: string;
  message?: string;
};

function postJson(
  url: URL,
  headers: Record<string, string>,
  body: string,
  options?: { timeoutMs?: number },
): Promise<{ status: number; data: ApiResponse }> {
  const doRequest = url.protocol === "https:" ? https.request : http.request;
  return new Promise((resolve, reject) => {
    const timeoutMs =
      typeof options?.timeoutMs === "number" &&
      Number.isFinite(options.timeoutMs) &&
      options.timeoutMs > 0
        ? Math.floor(options.timeoutMs)
        : DEFAULT_IMAGE_REQUEST_TIMEOUT_MS;
    let settled = false;
    const finish = (cb: () => void) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      cb();
    };

    const req = doRequest(
      url,
      {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => chunks.push(chunk));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          try {
            const data = JSON.parse(raw) as ApiResponse;
            finish(() => resolve({ status: res.statusCode ?? 500, data }));
          } catch {
            finish(() => resolve({ status: res.statusCode ?? 500, data: { error: raw } }));
          }
        });
      },
    );
    const timeout = setTimeout(() => {
      finish(() =>
        reject(new Error(`Pazi image generation request timed out after ${timeoutMs}ms`)),
      );
      req.destroy();
    }, timeoutMs);
    req.on("error", (err) => {
      finish(() => reject(err));
    });
    req.write(body);
    req.end();
  });
}

export function buildPaziImageGenerationProvider(params?: {
  pluginConfig?: Record<string, unknown> | null;
  env?: NodeJS.ProcessEnv;
}): ImageGenerationProvider {
  return {
    id: PAZI_PROVIDER_ID,
    label: "Pazi (GPT Image)",
    defaultModel: PAZI_IMAGE_MODEL,
    models: [PAZI_IMAGE_MODEL],
    capabilities: {
      generate: {
        maxCount: 1,
        supportsSize: true,
        supportsAspectRatio: false,
        supportsResolution: false,
      },
      edit: {
        enabled: false,
        maxCount: 0,
        maxInputImages: 0,
        supportsSize: false,
        supportsAspectRatio: false,
        supportsResolution: false,
      },
      geometry: {
        sizes: [...SUPPORTED_SIZES],
      },
    },
    async generateImage(req) {
      const context = getProxyContext();
      if (!context) {
        throw new Error("Pazi proxy context not available — cannot generate image");
      }
      markProxyActivity();

      const resolved = resolvePaziBillingConfig({
        pluginConfig: params?.pluginConfig,
        env: params?.env,
      });

      if (!resolved.apiUrl) {
        throw new Error("PAZI_API_URL not configured — cannot generate image");
      }

      // image_generate currently has no first-class quality field,
      // so keep provider quality fixed to the API default.
      const quality = "medium";
      const size = mapSize(req.size);

      const target = new URL("/images/generate", resolved.apiUrl);
      const body = JSON.stringify({
        prompt: req.prompt,
        quality,
        size,
        model: req.model || PAZI_IMAGE_MODEL,
      });

      const { status, data } = await postJson(
        target,
        {
          "X-Proxy-Token": context.proxyToken,
          "X-User-Id": context.userId,
          "X-Agent-Id": context.agentId,
        },
        body,
        { timeoutMs: req.timeoutMs },
      );

      if (status === 402) {
        throw new Error("Insufficient credits for image generation. Ask the user to add credits.");
      }
      if (status === 400 && data.error === "content_policy") {
        throw new Error(data.message ?? "Image generation blocked by content policy.");
      }
      if (status === 504) {
        throw new Error("Image generation timed out. Please try again.");
      }
      if (status !== 200 || !data.b64_json) {
        throw new Error(
          `Pazi image generation failed (${status}): ${data.message ?? data.error ?? "unknown error"}`,
        );
      }

      return {
        images: [
          {
            buffer: Buffer.from(data.b64_json, "base64"),
            mimeType: "image/png",
            fileName: "generated-image.png",
            revisedPrompt: data.revisedPrompt,
            metadata: {
              imageId: data.imageId,
              costUsd: data.costUsd,
              creditsDeducted: data.creditsDeducted,
              quality: data.quality,
              size: data.size,
            },
          },
        ],
        model: req.model || PAZI_IMAGE_MODEL,
        metadata: {
          imageId: data.imageId,
          // TODO(PAZ-282): b64_json here is a temporary unblock for dev/QA — ~300KB+ over
          // WebSocket per generation. Production path should rely on presigned S3 URLs via
          // imageId + GET /images/:imageId/url. Remove b64_json once S3 storage is reliable.
          b64_json: data.b64_json,
          costUsd: data.costUsd,
          creditsDeducted: data.creditsDeducted,
        },
      };
    },
  };
}
