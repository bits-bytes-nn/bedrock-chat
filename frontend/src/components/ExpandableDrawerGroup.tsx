import React, { ReactNode, useState } from 'react';
import { PiCaretDown } from 'react-icons/pi';
import { twMerge } from 'tailwind-merge';

type Props = {
  className?: string;
  label: string;
  children: ReactNode;
  isDefaultShow?: boolean;
  /** Keeps the drawer open, for example while it holds an error. */
  isForcedShow?: boolean;
};

const ExpandableDrawerGroup: React.FC<Props> = ({
  isDefaultShow = true,
  isForcedShow = false,
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(isDefaultShow);
  const isShow = isOpen || isForcedShow;

  return (
    <div className={twMerge(props.className)}>
      <div
        className="flex w-full cursor-pointer items-center transition hover:brightness-75"
        onClick={() => {
          setIsOpen(!isShow);
        }}>
        <PiCaretDown className={`mx-1 text-sm ${isShow ? '' : 'rotate-180'}`} />

        <div className="italic">{props.label}</div>
      </div>
      <div className="">
        <div
          className={`origin-top transition-all ${
            isShow ? 'visible' : 'h-0 scale-y-0'
          }`}>
          {props.children}
        </div>
      </div>
    </div>
  );
};

export default ExpandableDrawerGroup;
