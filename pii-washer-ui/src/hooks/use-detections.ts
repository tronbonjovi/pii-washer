import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  updateDetectionStatus,
  editDetectionPlaceholder,
  confirmAllDetections,
  addManualDetection,
} from '@/api/detections';
import type { PIICategory } from '@/types/api';

export function useUpdateDetectionStatus(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ detectionId, status }: { detectionId: string; status: 'pending' | 'confirmed' | 'rejected' }) =>
      updateDetectionStatus(sessionId, detectionId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', sessionId] });
    },
  });
}

export function useEditPlaceholder(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ detectionId, placeholder }: { detectionId: string; placeholder: string }) =>
      editDetectionPlaceholder(sessionId, detectionId, placeholder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

export function useConfirmAllDetections(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => confirmAllDetections(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', sessionId] });
    },
  });
}

export function useAddManualDetection(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ textValue, category }: { textValue: string; category: PIICategory }) =>
      addManualDetection(sessionId, textValue, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', sessionId] });
    },
  });
}
