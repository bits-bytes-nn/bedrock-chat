import { sharedKnowledgeBasesStackName } from "../../lib/utils/stack-names";

describe("sharedKnowledgeBasesStackName", () => {
  test("keeps the name of existing deployments in the default environment", () => {
    expect(sharedKnowledgeBasesStackName("")).toBe("BrChatSharedKbStack");
  });

  test("prefixes the name with the environment", () => {
    expect(sharedKnowledgeBasesStackName("dev")).toBe("dev-BrChatSharedKbStack");
  });
});
