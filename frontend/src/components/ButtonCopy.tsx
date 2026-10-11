import React, { useCallback, useState } from 'react';
import ButtonIcon from './ButtonIcon';
import { BaseProps } from '../@types/common';
import { PiCheck, PiClipboard } from 'react-icons/pi';
import copy from 'copy-to-clipboard';
import { useTranslation } from 'react-i18next';

type Props = BaseProps & {
  text: string;
};

const ButtonCopy: React.FC<Props> = (props) => {
  const { t } = useTranslation();
  const [showsCheck, setshowsCheck] = useState(false);

  const copyMessage = useCallback((message: string) => {
    copy(message);
    setshowsCheck(true);

    setTimeout(() => {
      setshowsCheck(false);
    }, 3000);
  }, []);

  return (
    <ButtonIcon
      className={props.className}
      label={t('button.copy')}
      onClick={() => {
        copyMessage(props.text);
      }}>
      {showsCheck ? <PiCheck /> : <PiClipboard />}
    </ButtonIcon>
  );
};

export default ButtonCopy;
