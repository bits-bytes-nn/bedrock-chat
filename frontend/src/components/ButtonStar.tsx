import { useTranslation } from 'react-i18next';
import React from 'react';
import ButtonIcon from './ButtonIcon';
import { PiStar, PiStarFill } from 'react-icons/pi';
import { BaseProps } from '../@types/common';
import { twMerge } from 'tailwind-merge';

type Props = BaseProps & {
  isStarred: boolean;
  disabled?: boolean;
  onClick: () => void;
};

const ButtonStar: React.FC<Props> = (props) => {
  const { t } = useTranslation();
  return (
    <ButtonIcon
      label={props.isStarred ? t('button.unstar') : t('button.star')}
      className={twMerge(props.className)}
      disabled={props.disabled}
      onClick={props.onClick}>
      {props.isStarred ? <PiStarFill className="text-aws-aqua" /> : <PiStar />}
    </ButtonIcon>
  );
};

export default ButtonStar;
