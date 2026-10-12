import InputChatContent from './InputChatContent';
import { useState } from 'react';
import type { StoryDefault } from '@ladle/react';
import { MemoryRouter } from 'react-router-dom';

export default {
  decorators: [
    (Component) => (
      <MemoryRouter>
        <Component />
      </MemoryRouter>
    ),
  ],
} satisfies StoryDefault;

const defaultProps = {
  reasoningEnabled: false,
  onChangeReasoning: () => {},
  supportReasoning: true,
  isLoading: false,
  isNewChat: false,
  onSend: () => {},
  onRegenerate: () => {},
  continueGenerate: () => {},
};

export const Ideal = () => {
  const [reasoningEnabled, setReasoningEnabled] = useState(false);
  return (
    <InputChatContent
      {...defaultProps}
      canRegenerate={false}
      canContinue={false}
      reasoningEnabled={reasoningEnabled}
      onChangeReasoning={() => setReasoningEnabled(!reasoningEnabled)}
    />
  );
};

export const IdealLoading = () => {
  const [reasoningEnabled, setReasoningEnabled] = useState(false);
  return (
    <InputChatContent
      {...defaultProps}
      canRegenerate={false}
      canContinue={false}
      reasoningEnabled={reasoningEnabled}
      onChangeReasoning={() => setReasoningEnabled(!reasoningEnabled)}
      isLoading={true}
    />
  );
};

export const IdealDisabled = () => {
  const [reasoningEnabled, setReasoningEnabled] = useState(false);
  return (
    <InputChatContent
      {...defaultProps}
      canRegenerate={false}
      canContinue={false}
      reasoningEnabled={reasoningEnabled}
      onChangeReasoning={() => setReasoningEnabled(!reasoningEnabled)}
      disabled={true}
    />
  );
};

export const WithRegenerate = () => {
  const [reasoningEnabled, setReasoningEnabled] = useState(false);
  return (
    <InputChatContent
      {...defaultProps}
      canRegenerate={true}
      canContinue={false}
      reasoningEnabled={reasoningEnabled}
      onChangeReasoning={() => setReasoningEnabled(!reasoningEnabled)}
    />
  );
};

export const WithContinue = () => {
  const [reasoningEnabled, setReasoningEnabled] = useState(false);
  return (
    <InputChatContent
      {...defaultProps}
      canRegenerate={true}
      canContinue={true}
      reasoningEnabled={reasoningEnabled}
      onChangeReasoning={() => setReasoningEnabled(!reasoningEnabled)}
    />
  );
};
