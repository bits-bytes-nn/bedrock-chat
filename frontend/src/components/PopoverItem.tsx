import React, { ReactNode } from 'react';

type Props = {
  className?: string;
  children: ReactNode;
  onClick: () => void;
};

const PopoverItem: React.FC<Props> = (props) => {
  return (
    <button
      type="button"
      className={`${
        props.className ?? ''
      } flex w-full cursor-pointer items-center gap-1 border-b border-aws-font-color-light/50 bg-aws-paper-light px-2 py-1 text-left first:rounded-t-sm last:rounded-b-sm last:border-b-0 hover:brightness-75 dark:border-aws-font-color-dark/50 dark:bg-aws-paper-dark`}
      onClick={props.onClick}>
      {props.children}
    </button>
  );
};

export default PopoverItem;
