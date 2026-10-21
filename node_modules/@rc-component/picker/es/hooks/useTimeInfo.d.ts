import type { GenerateConfig } from '../generate';
import type { SharedTimeProps } from '../interface';
export type Unit<ValueType = number | string> = {
    label: string | number;
    value: ValueType;
    disabled?: boolean;
};
/**
 * Parse time props to get util info
 */
export default function useTimeInfo<DateType extends object = any>(generateConfig: GenerateConfig<DateType>, props?: SharedTimeProps<DateType>, date?: DateType): readonly [(nextTime: DateType, certainDate?: DateType) => DateType, Unit<number>[], (nextHour: number) => Unit<number>[], (nextHour: number, nextMinute: number) => Unit<number>[], (nextHour: number, nextMinute: number, nextSecond: number) => Unit<number>[]];
