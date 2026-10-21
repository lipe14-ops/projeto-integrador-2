import * as React from 'react';
interface FocusLockSelectorRef {
    startInput: HTMLElement;
    endInput: HTMLElement;
    focus: (index?: number) => void;
}
/**
 * Keep focus on the specified input field while focus moves inside the Picker.
 * 当焦点在 Picker 内移动时，将其锁定在指定的输入框上。
 */
export default function useFocusLock(index: number | null, forceFocus: boolean, selectorRef: React.RefObject<FocusLockSelectorRef | null>, popupRef: React.RefObject<HTMLElement | null>, triggerOpen: (open: boolean) => void): void;
export {};
