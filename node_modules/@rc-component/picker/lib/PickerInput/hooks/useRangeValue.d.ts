import type { GenerateConfig } from '../../generate';
import type { BaseInfo, FormatType, Locale, ReplaceListType } from '../../interface';
import type { RangePickerProps } from '../RangePicker';
import type { ReplacedPickerProps } from '../SinglePicker';
type TriggerCalendarChange<ValueType extends object[]> = (calendarValues: ValueType) => void;
/**
 * Control the internal `value` align with prop `value` and provide a temp `calendarValue` for ui.
 * The caller controls the temporary `calendarValue` lifecycle through event handlers.
 */
export declare function useInnerValue<ValueType extends DateType[], DateType extends object = any>(generateConfig: GenerateConfig<DateType>, locale: Locale, formatList: FormatType[], 
/** Used for RangePicker. `true` means [DateType, DateType] or will be DateType[] */
rangeValue: boolean, 
/**
 * Trigger order when trigger calendar value change.
 * This should only used in SinglePicker with `multiple` mode.
 * So when `rangeValue` is `true`, order will be ignored.
 */
order: boolean, defaultValue?: ValueType, value?: ValueType, onCalendarChange?: (dates: ValueType, dateStrings: ReplaceListType<Required<ValueType>, string>, info: BaseInfo) => void, onOk?: (dates: ValueType) => void): readonly [ValueType, (updater: ValueType | ((origin: ValueType) => ValueType)) => void, (useControlledValueFirst?: boolean) => ValueType, TriggerCalendarChange<ValueType>, () => void];
export default function useRangeValue<ValueType extends DateType[], DateType extends object = any>(info: Pick<RangePickerProps<DateType>, 'generateConfig' | 'locale' | 'allowEmpty' | 'order' | 'picker'> & ReplacedPickerProps<DateType>, mergedValue: ValueType, setInnerValue: (nextValue: ValueType) => void, getCalendarValue: () => ValueType, triggerCalendarChange: TriggerCalendarChange<ValueType>, disabled: ReplaceListType<Required<ValueType>, boolean>, formatList: FormatType[], isInvalidateDate: (date: DateType, info?: {
    from?: DateType;
    activeIndex: number;
}) => boolean): [
    /** Trigger `onChange` by check `disabledDate` */
    flushSubmit: (index: number, needTriggerChange: boolean) => void,
    /** Trigger `onChange` directly without check `disabledDate` */
    triggerSubmitChange: (value: ValueType) => boolean,
    /** Reset calendar and submit values back to the committed value */
    resetValue: (index?: number) => void
];
export {};
