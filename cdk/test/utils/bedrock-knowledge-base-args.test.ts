import { ChunkingStrategy } from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock/data-sources/chunking";
import {
  getChunkingOptions,
  getChunkingStrategy,
  getParsingModel,
} from "../../lib/utils/bedrock-knowledge-base-args";

describe("getParsingModel", () => {
  test("falls back to the default parser for retired models", () => {
    expect(getParsingModel("anthropic.claude-3-5-sonnet-v1")).toBeUndefined();
    expect(getParsingModel("anthropic.claude-3-sonnet-v1")).toBeUndefined();
  });

  test("keeps the available models", () => {
    expect(getParsingModel("anthropic.claude-3-haiku-v1")).toBeDefined();
    expect(getParsingModel("anthropic.claude-haiku-4-5")?.invokableArn).toContain(
      "inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"
    );
  });
});

describe("getChunkingOptions", () => {
  test("keeps parameters that are 0", () => {
    const options = getChunkingOptions({
      chunking_strategy: "semantic",
      max_tokens: 300,
      buffer_size: 0,
      breakpoint_percentile_threshold: 95,
      overlap_percentage: 0,
    });
    expect(options.bufferSize).toBe(0);
    expect(options.overlapPercentage).toBe(0);
  });

  test("maps missing or null parameters to undefined", () => {
    expect(getChunkingOptions(undefined).maxTokens).toBeUndefined();
    expect(getChunkingOptions({ max_tokens: null }).maxTokens).toBeUndefined();
  });

  test("builds a custom semantic strategy when bufferSize is 0", () => {
    const options = getChunkingOptions({
      max_tokens: 300,
      buffer_size: 0,
      breakpoint_percentile_threshold: 90,
    });
    const strategy = getChunkingStrategy("semantic", "titan_v2", options);
    expect(strategy).not.toBe(ChunkingStrategy.SEMANTIC);
    expect(strategy.configuration).toEqual({
      chunkingStrategy: "SEMANTIC",
      semanticChunkingConfiguration: {
        maxTokens: 300,
        bufferSize: 0,
        breakpointPercentileThreshold: 90,
      },
    });
  });
});
