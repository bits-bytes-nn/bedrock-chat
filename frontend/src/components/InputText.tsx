import React, {
  HTMLInputTypeAttribute,
  KeyboardEvent,
  ReactNode,
  useId,
} from 'react';
import { twMerge } from 'tailwind-merge';

type Props = {
  className?: string;
  label?: string;
  type?: HTMLInputTypeAttribute;
  value: string;
  disabled?: boolean;
  placeholder?: string;
  hint?: string;
  errorMessage?: string;
  icon?: ReactNode;
  onChange?: (s: string) => void;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
};

const InputText = React.forwardRef<HTMLInputElement, Props>((props, ref) => {
  const id = useId();
  return (
    <div className={twMerge('flex flex-col', props.className)}>
      {props.icon && (
        <div className="relative inline-block">
          <div className="absolute left-2 top-2 text-lg">{props.icon}</div>
        </div>
      )}
      <input
        id={id}
        ref={ref}
        type={props.type ?? 'text'}
        className={twMerge(
          'peer h-9 rounded border p-1 dark:[color-scheme:dark]',
          'dark:bg-aws-ui-color-dark dark:text-aws-font-color-dark dark:placeholder-aws-font-color-gray',
          props.errorMessage
            ? 'border-2 border-red'
            : 'border-aws-font-color-light/50 dark:border-aws-font-color-dark/50',
          props.icon ? 'pl-8' : ''
        )}
        disabled={props.disabled}
        aria-invalid={!!props.errorMessage}
        aria-describedby={props.errorMessage ? `${id}-error` : undefined}
        value={props.value}
        placeholder={props.placeholder}
        onChange={(e) => {
          props.onChange?.(e.target.value);
        }}
        onKeyDown={props.onKeyDown}
      />

      {props.label && (
        <label
          htmlFor={id}
          className={twMerge(
            'order-first text-sm peer-focus:font-semibold peer-focus:italic',
            props.errorMessage
              ? 'font-bold text-red dark:text-red-400'
              : 'text-aws-font-color-light/80 peer-focus:text-aws-font-color-light dark:text-light-gray dark:peer-focus:text-aws-font-color-dark'
          )}>
          {props.label}
        </label>
      )}
      {props.hint && !props.errorMessage && (
        <div className="mt-0.5 text-xs text-aws-font-color-light/70 dark:text-aws-font-color-dark">
          {props.hint}
        </div>
      )}
      {props.errorMessage && (
        <div id={`${id}-error`} className="mt-0.5 text-xs text-red dark:text-red-400">
          {props.errorMessage}
        </div>
      )}
    </div>
  );
});

InputText.displayName = 'InputText';

export default InputText;
