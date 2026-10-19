import React, { ReactNode, useEffect, useState } from 'react';
import { PiCaretDown } from 'react-icons/pi';
import { twMerge } from 'tailwind-merge';

type Props = {
  className?: string;
  label: string;
  children: ReactNode;
  isDefaultShow?: boolean;
  /** Opens the drawer whenever it turns true, for example to show an error inside. */
  isForcedShow?: boolean;
};

const ExpandableDrawerGroup: React.FC<Props> = ({
  isDefaultShow = true,
  isForcedShow = false,
  ...props
}) => {
  const [isShow, setIsShow] = useState(isDefaultShow || isForcedShow);

  useEffect(() => {
    if (isForcedShow) {
      setIsShow(true);
    }
  }, [isForcedShow]);

  return (
    <div className={twMerge(props.className)}>
      <div
        className="flex w-full cursor-pointer items-center transition hover:brightness-75"
        onClick={() => {
          setIsShow(!isShow);
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
