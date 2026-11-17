import { describe, expect, test } from 'vitest';
import { getSearchStatus } from '../useConversationSearch';

describe('getSearchStatus', () => {
  test('shows nothing without a query', () => {
    expect(getSearchStatus('', '', false)).toEqual({
      hasSearched: false,
      isSearching: false,
    });
  });

  test('is searching while the user types', () => {
    // The debounced query is still empty, so there are no results yet.
    expect(getSearchStatus('rep', '', false).isSearching).toBe(true);
    // The results are for an earlier query.
    expect(getSearchStatus('report', 'rep', false).isSearching).toBe(true);
  });

  test('is searching while the results load', () => {
    expect(getSearchStatus('report', 'report', true).isSearching).toBe(true);
  });

  test('shows the results of the current query', () => {
    expect(getSearchStatus('report', 'report', false)).toEqual({
      hasSearched: true,
      isSearching: false,
    });
  });
});
