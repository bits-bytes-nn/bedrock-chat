import { SearchApiConfig, SearchEngine } from '../types';

export const DEFAULT_SEARCH_API_CONFIG: SearchApiConfig = {
  apiKey: '',
  maxResults: 5,
};

// The search engines that need an API key, with the most results that each one
// returns, as SEARCH_API_MAX_RESULTS in backend/app/routes/schemas/bot.py.
export const SEARCH_API_MAX_RESULTS: Partial<Record<SearchEngine, number>> = {
  firecrawl: 100,
  tavily: 20,
  brave: 20,
};
