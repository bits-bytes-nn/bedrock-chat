module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/test'],
  testMatch: ['**/*.test.ts'],
  setupFilesAfterEnv: ['<rootDir>/test/setup-tmpdir.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  }
};
