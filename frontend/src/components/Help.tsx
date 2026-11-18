import React, { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { BaseProps } from '../@types/common';
import { PiQuestionFill } from 'react-icons/pi';
import Tooltip from './Tooltip';
import { Direction } from '../constants';

type Props = BaseProps & {
  message: string;
  direction?: Direction;
};

const Help: React.FC<Props> = (props) => {
  const { t } = useTranslation();
  const messageId = useId();
  return (
    <Tooltip {...props} messageId={messageId}>
      {/* Focusable, so that keyboard and touch users can open the message. */}
      <button
        type="button"
        aria-label={t('button.help')}
        aria-describedby={messageId}
        className="align-middle">
        <PiQuestionFill />
      </button>
    </Tooltip>
  );
};

export default Help;
