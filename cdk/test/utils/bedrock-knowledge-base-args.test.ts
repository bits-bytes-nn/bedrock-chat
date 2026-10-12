import { getParsingModel } from "../../lib/utils/bedrock-knowledge-base-args";

describe("getParsingModel", () => {
  test("falls back to the default parser for retired models", () => {
    expect(getParsingModel("anthropic.claude-3-5-sonnet-v1")).toBeUndefined();
    expect(getParsingModel("anthropic.claude-3-sonnet-v1")).toBeUndefined();
  });

  test("keeps the available model", () => {
    expect(getParsingModel("anthropic.claude-3-haiku-v1")).toBeDefined();
  });
});
