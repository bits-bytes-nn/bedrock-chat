import { useState, useCallback } from 'react';
import { useDebounce } from 'use-debounce';
import useConversationSearchApi from './useConversationSearchApi';

// Debounce delay in milliseconds
const DEBOUNCE_DELAY = 300;

/**
 * Whether a search is shown and whether its results are still coming. While the
 * user types, the debounced query and its results belong to the earlier text.
 */
export const getSearchStatus = (
  query: string,
  debouncedQuery: string,
  isLoading: boolean
) => {
  const hasSearched = query !== '';
  return {
    hasSearched,
    isSearching: isLoading || (hasSearched && query !== debouncedQuery),
  };
};

function useConversationSearch() {
  const conversationSearchApi = useConversationSearchApi();
  const [searchQuery, setSearchQuery] = useState('');
  const query = searchQuery.trim();
  const [debouncedQuery] = useDebounce(query, DEBOUNCE_DELAY);

  const {
    data: searchResults,
    error: searchError,
    isLoading,
    mutate: refreshSearchResults,
  } = conversationSearchApi.searchConversations(debouncedQuery || null);

  const { hasSearched, isSearching } = getSearchStatus(
    query,
    debouncedQuery,
    isLoading
  );

  const clearSearch = useCallback(() => setSearchQuery(''), []);
  const retrySearch = useCallback(() => {
    refreshSearchResults();
  }, [refreshSearchResults]);

  return {
    searchResults: searchResults ?? [],
    isSearching,
    isSearchError: !!searchError,
    hasSearched,
    displayQuery: debouncedQuery,
    handleSearch: setSearchQuery,
    clearSearch,
    retrySearch,
  };
}

export default useConversationSearch;
