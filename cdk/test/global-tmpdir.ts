import * as fs from "fs";
import * as os from "os";
import * as path from "path";

// Code.fromDockerBuild copies the built code into os.tmpdir() while a stack is
// constructed, about 60 MB each time, and never removes it. The test workers get
// their own TMPDIR, which is removed after the run. It is set here because the
// workers inherit the environment of this process; a test file only changes its
// own copy of process.env.
const variable = "BEDROCK_CHAT_CDK_TEST_TMPDIR";

export default function setup(): void {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bedrock-chat-cdk-test-"));
  process.env[variable] = dir;
  process.env.TMPDIR = dir;
}

export function teardown(): void {
  const dir = process.env[variable];
  if (dir) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
