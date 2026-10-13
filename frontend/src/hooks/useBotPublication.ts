import useBotPublicationApi from './useBotPublicationApi';

const useBotPublication = (botId: string) => {
  const { getBotPublication } = useBotPublicationApi();

  const { data, isLoading, error, mutate } = getBotPublication(
    botId,
    undefined,
    {
      // An unpublished bot answers 404, which retrying does not change.
      shouldRetryOnError: false,
      // Follow the deployment, which runs in CodeBuild and CloudFormation.
      refreshInterval: (publication) =>
        publication &&
        (publication.codebuildStatus === 'IN_PROGRESS' ||
          publication.cfnStatus?.endsWith('_IN_PROGRESS'))
          ? 10000
          : 0,
    }
  );

  return {
    botPublication: data,
    isLoading,
    error,
    mutate,
  };
};

export default useBotPublication;
