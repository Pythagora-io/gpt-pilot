// Public gateway/client helpers for plugins that talk to the host gateway surface.

export * from "../gateway/channel-status-patches.js";
export { GatewayClient } from "../gateway/client.js";
export {
  createOperatorApprovalsGatewayClient,
  withOperatorApprovalsGatewayClient,
} from "../gateway/operator-approvals-client.js";
export { ErrorCodes, errorShape } from "../gateway/protocol/index.js";
export type { EventFrame } from "../gateway/protocol/index.js";
export type { GatewayRequestHandler, GatewayRequestHandlerOptions } from "../gateway/server-methods/types.js";
