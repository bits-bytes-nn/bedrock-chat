import { GetBotPublicationResponse } from '../@types/api-publication';

type DeployStatus = Pick<
  GetBotPublicationResponse,
  'codebuildStatus' | 'cfnStatus'
>;

// CodeBuild build statuses of a build that ended without success.
const FAILED_BUILD_STATUSES = ['FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT'];

/**
 * Whether the deployment of a published API failed: the build ended without
 * success, or the stack failed or was rolled back.
 */
export const hasDeployFailed = (publication: DeployStatus): boolean =>
  FAILED_BUILD_STATUSES.includes(publication.codebuildStatus) ||
  publication.cfnStatus.endsWith('_FAILED') ||
  publication.cfnStatus.endsWith('ROLLBACK_COMPLETE');

/** Whether the deployment of a published API is still running. */
export const isDeploying = (publication: DeployStatus): boolean =>
  !hasDeployFailed(publication) &&
  (publication.codebuildStatus === 'IN_PROGRESS' ||
    publication.cfnStatus.endsWith('_IN_PROGRESS'));
