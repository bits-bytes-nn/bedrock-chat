import React, { useMemo } from 'react';
import { BaseProps } from '../@types/common';
import { PiInfo, PiWarningCircleFill, PiWarningFill } from 'react-icons/pi';
import { twMerge } from 'tailwind-merge';

type Props = BaseProps & {
  severity: 'info' | 'warning' | 'error';
  title?: string;
  children: React.ReactNode;
};

const Alert: React.FC<Props> = (props) => {
  const icon = useMemo(() => {
    switch (props.severity) {
      case 'info':
        return <PiInfo className="text-2xl" />;
      case 'warning':
        return <PiWarningFill className="text-2xl" />;
      case 'error':
        return <PiWarningCircleFill className="text-2xl" />;
    }
  }, [props.severity]);

  // White text is too faint on yellow (2.2:1), and light gray too faint on red and aqua.
  const textColor =
    props.severity === 'warning'
      ? 'text-aws-font-color-light'
      : 'text-aws-font-color-white-light';

  return (
    <div
      className={twMerge(
        'flex flex-col rounded border border-aws-squid-ink-light shadow-lg dark:border-aws-squid-ink-dark',
        props.severity === 'info' && 'bg-aws-aqua',
        props.severity === 'warning' && 'bg-yellow',
        props.severity === 'error' && 'bg-red',
        props.className
      )}>
      {props.title && (
        <div
          className={twMerge(
            'flex gap-2 px-2 pt-2 font-bold',
            textColor
          )}>
          {icon}
          <div>{props.title}</div>
        </div>
      )}

      <div className={twMerge('p-2', textColor)}>
        {props.children}
      </div>
    </div>
  );
};

export default Alert;
