import * as React from 'react';
import type { PickerRef } from '../../interface';
type PickerRefType<OptionType> = Omit<PickerRef, 'focus'> & {
    focus: (options?: OptionType) => void;
};
export default function usePickerRef<OptionType, SelectorRefType extends PickerRefType<OptionType> = PickerRefType<OptionType>>(ref: React.Ref<PickerRefType<OptionType>>): React.RefObject<SelectorRefType>;
export {};
