/**
 * CloudWatch namespace of the app's own metrics (backend/app/metrics.py). Environments
 * in the same account and Region get their own, so their alarms stay apart.
 */
export const metricsNamespace = (envPrefix: string): string =>
  envPrefix ? `BedrockChat/${envPrefix}` : "BedrockChat";
