import { getParsingModel } from "../../lib/utils/bedrock-knowledge-base-args";

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
