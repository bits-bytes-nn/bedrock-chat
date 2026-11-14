module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/test'],
  testMatch: ['**/*.test.ts'],
  globalSetup: '<rootDir>/test/global-tmpdir.ts',
  globalTeardown: '<rootDir>/test/global-teardown.ts',
  setupFilesAfterEnv: ['<rootDir>/test/setup-tmpdir.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  }
};
