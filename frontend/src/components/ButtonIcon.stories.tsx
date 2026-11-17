import { PiPlus } from 'react-icons/pi';
import ButtonIcon from './ButtonIcon';

export const Ideal = () => (
  <ButtonIcon label="Add" onClick={() => {}}>
    <PiPlus />
  </ButtonIcon>
);

export const Disabled = () => (
  <ButtonIcon label="Add" disabled onClick={() => {}}>
    <PiPlus />
  </ButtonIcon>
);
