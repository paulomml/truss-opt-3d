export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

const toasts = ref<Toast[]>([]);

export const useToast = () => {
  const addToast = (message: string, type: ToastType = "info") => {
    const id = Date.now();
    toasts.value.push({ id, message, type });

    // Previne memory leaks e poluição da DOM em fluxos com alto volume de erros (WS reconnection).
    setTimeout(() => {
      removeToast(id);
    }, 5000);
  };

  const removeToast = (id: number) => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  };

  return {
    toasts: readonly(toasts),
    addToast,
    removeToast,
  };
};
