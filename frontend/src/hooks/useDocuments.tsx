// frontend/src/hooks/useDocuments.ts
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { documentsApi } from "../api/documents";

export const DOCUMENTS_KEY = ["documents"] as const;

export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: () => documentsApi.list(),
    refetchInterval: (query) => {
      // Poll every 3 seconds if any document is still processing
      const docs = query.state.data?.documents ?? [];
      const hasPending = docs.some(
        (d) => d.status === "pending" || d.status === "processing"
      );
      return hasPending ? 3000 : false;
    },
  });
}

export function useDocumentStatus(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["document", id, "status"],
    queryFn: () => documentsApi.getStatus(id),
    enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "processing" ? 2000 : false;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, description }: { file: File; description?: string }) =>
      documentsApi.upload(file, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}