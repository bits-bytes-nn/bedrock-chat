import { metricsNamespace } from "../../lib/utils/metrics";

describe("metricsNamespace", () => {
  test("keeps the default environment's namespace and separates the others", () => {
    expect(metricsNamespace("")).toBe("BedrockChat");
    expect(metricsNamespace("dev")).toBe("BedrockChat/dev");
  });
});
