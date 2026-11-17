import { useTranslation } from 'react-i18next';
import React, { useEffect } from 'react';
import { PiWarningFill, PiX } from 'react-icons/pi';
import ButtonIcon from '../components/ButtonIcon';
import useSnackbar from '../hooks/useSnackbar';
import { Transition } from '@headlessui/react';

type Props = {
  children: React.ReactNode;
};

const SNACKBAR_DURATION_MS = 5000;

const SnackbarProvider: React.FC<Props> = ({ children }) => {
  const { t } = useTranslation();
  const { isOpen, close, message, openCount } = useSnackbar();

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    // Close automatically 5 seconds after the latest message.
    const timer = setTimeout(close, SNACKBAR_DURATION_MS);
    return () => clearTimeout(timer);
  }, [close, isOpen, openCount]);

  return (
    <>
      <div className="fixed top-0 left-0 z-50 w-full lg:left-1/3 lg:w-1/2">
        <Transition
          show={isOpen}
          enter="transform transition duration-75"
          enterFrom="opacity-0 scale-50"
          enterTo="opacity-100 scale-100"
          leave="transform duration-200 transition ease-in-out"
          leaveFrom="opacity-100 scale-100 "
          leaveTo="opacity-0 scale-95 ">
          <div className="">
            <div
              role="alert"
              className="mx-4 mt-4 flex justify-between rounded-sm bg-red p-3 text-sm text-aws-font-color-white-light shadow-lg">
              <div className="mr-3 text-3xl">
                <PiWarningFill />
              </div>
              <div className="grow">{message}</div>
              <div className="-mt-2 -mr-2">
                <ButtonIcon label={t('button.close')} onClick={close}>
                  <PiX />
                </ButtonIcon>
              </div>
            </div>
          </div>
        </Transition>
      </div>
      {children}
    </>
  );
};

export default SnackbarProvider;
