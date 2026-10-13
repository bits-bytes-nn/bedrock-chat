export const excludeDockerImage = [
  ".mypy_cache",
  ".venv",
  "test",
  "tests",
  "node_modules",
  "dist",
  "dev-dist",
  ".env",
  ".env.local",
]

/** Poetry that bundles the backend for the Python Lambda functions. */
export const POETRY_VERSION = "1.8.5";