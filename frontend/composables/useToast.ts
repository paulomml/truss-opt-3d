export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

const toasts = ref<Toast[]>([]);

export const useToast = () => {
  /*
   Lógica de gerenciamento do estado das notificações de sistema.
   O ciclo de vida das mensagens é controlado para garantir a comunicação de alertas técnicos ao usuário.
  */
  const addToast = (message: string, type: ToastType = "info") => {
    const id = Date.now();
    toasts.value.push({ id, message, type });

    // Descarte automático após intervalo definido para limpeza do buffer visual.
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
