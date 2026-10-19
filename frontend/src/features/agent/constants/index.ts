import { SearchApiConfig, SearchEngine } from '../types';

export const DEFAULT_SEARCH_API_CONFIG: SearchApiConfig = {
  apiKey: '',
  maxResults: 5,
};

// The search engines that need an API key, with the most results to request.
// The backend accepts up to SEARCH_API_MAX_RESULTS in app/routes/schemas/bot.py.
export const SEARCH_API_MAX_RESULTS: Partial<Record<SearchEngine, number>> = {
  firecrawl: 50,
  tavily: 20,
  brave: 20,
};
