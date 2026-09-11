import { useInfiniteQuery } from "@tanstack/react-query";
import api from "@/api/axios";
import type { PaginatedResponse } from "@/federation/types";

const DEFAULT_PAGE_SIZE = 100;

/**
 * Reusable hook for paginated fetches against the v1 OMOP clinical endpoints.
 * Returns accumulated results across all fetched pages plus infinite-query controls.
 */
export function useInfiniteOmopQuery<T>(
  endpoint: string,
  personId: number | undefined,
  pageSize = DEFAULT_PAGE_SIZE,
) {
  const query = useInfiniteQuery<PaginatedResponse<T>>({
    queryKey: ["clinical-summary", endpoint, personId, pageSize],
    queryFn: async ({ pageParam }) => {
      const resp = await api.get<PaginatedResponse<T>>(
        `/v1/${endpoint}/`,
        { params: { person_id: personId, page: pageParam, page_size: pageSize } },
      );
      return resp.data;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage, _allPages, lastPageParam) =>
      lastPage.next ? (lastPageParam as number) + 1 : undefined,
    enabled: !!personId,
  });

  const allResults = query.data?.pages.flatMap((p) => p.results) ?? [];
  const totalCount = query.data?.pages[0]?.count ?? 0;

  return {
    ...query,
    allResults,
    totalCount,
  };
}
