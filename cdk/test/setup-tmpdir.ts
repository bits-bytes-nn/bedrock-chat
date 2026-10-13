import * as fs from "fs";
import * as os from "os";
import * as path from "path";

// An App() without an outdir synthesizes into a new temporary directory that is
// never removed, and the source asset copies the repository there, so every run
// left gigabytes behind. The apps of a test file share one directory instead,
// which is removed afterwards. App reads CDK_OUTDIR from the test's environment.
const outdir = fs.mkdtempSync(path.join(os.tmpdir(), "bedrock-chat-cdk-test-"));
process.env.CDK_OUTDIR = outdir;

afterAll(() => {
  fs.rmSync(outdir, { recursive: true, force: true });
});
