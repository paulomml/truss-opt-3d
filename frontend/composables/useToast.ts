export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

const toasts = ref<Toast[]>([]);

export const useToast = () => {
  const addToast = (message: string, type: ToastType = 'info') => {
    const id = Date.now();
    toasts.value.push({ id, message, type });

    // Remove toast após 5s para evitar acúmulo na DOM.
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
