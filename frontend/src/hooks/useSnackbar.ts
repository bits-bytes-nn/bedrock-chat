import { create } from 'zustand';

export const useSnackbarState = create<{
  isOpen: boolean;
  message: string;
  // Incremented by every open, so that a new message restarts the close timer.
  openCount: number;
  open: (message: string) => void;
  close: () => void;
}>((set) => {
  return {
    isOpen: false,
    message: '',
    openCount: 0,
    open: (message) => {
      set((state) => ({
        isOpen: true,
        message,
        openCount: state.openCount + 1,
      }));
    },
    close: () => {
      set(() => ({
        isOpen: false,
      }));
    },
  };
});

const useSnackbar = () => {
  const { open, close, isOpen, message, openCount } = useSnackbarState();

  return {
    open,
    close,
    isOpen,
    message,
    openCount,
  };
};
export default useSnackbar;
