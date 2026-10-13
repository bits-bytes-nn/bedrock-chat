import { ListPublicBotsRequest } from '../@types/api-publication';
import useAdminApi from './useAdminApi';

const usePublicBotsForAdmin = (params: ListPublicBotsRequest) => {
  const { listPublicBots } = useAdminApi();

  const { data, error, isLoading, mutate } = listPublicBots(params);

  return {
    publicBots: data,
    error,
    isLoading,
    mutate,
  };
};

export default usePublicBotsForAdmin;
