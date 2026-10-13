import { describe, expect, it } from 'vitest';
import { hasDeployFailed, isDeploying } from '../PublicationUtils';

const status = (codebuildStatus: string, cfnStatus = '') => ({
  codebuildStatus,
  cfnStatus,
});

describe('hasDeployFailed', () => {
  it.each(['FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT'])(
    'is true when the build ended with %s',
    (codebuildStatus) => {
      expect(hasDeployFailed(status(codebuildStatus))).toBe(true);
    }
  );

  it.each([
    'CREATE_FAILED',
    'ROLLBACK_FAILED',
    'ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE',
  ])('is true when the stack is %s', (cfnStatus) => {
    expect(hasDeployFailed(status('SUCCEEDED', cfnStatus))).toBe(true);
  });

  it.each([
    status('IN_PROGRESS'),
    status('IN_PROGRESS', 'CREATE_IN_PROGRESS'),
    status('SUCCEEDED', 'CREATE_COMPLETE'),
  ])('is false for %o', (publication) => {
    expect(hasDeployFailed(publication)).toBe(false);
  });
});

describe('isDeploying', () => {
  it.each([
    status('IN_PROGRESS'),
    status('IN_PROGRESS', 'CREATE_IN_PROGRESS'),
    status('SUCCEEDED', 'CREATE_IN_PROGRESS'),
  ])('is true for %o', (publication) => {
    expect(isDeploying(publication)).toBe(true);
  });

  it.each([
    status('SUCCEEDED', 'CREATE_COMPLETE'),
    // The stack rolls back after the build failed: there is nothing to wait for.
    status('FAILED', 'ROLLBACK_IN_PROGRESS'),
    status('IN_PROGRESS', 'CREATE_FAILED'),
    status('TIMED_OUT'),
  ])('is false for %o', (publication) => {
    expect(isDeploying(publication)).toBe(false);
  });
});
