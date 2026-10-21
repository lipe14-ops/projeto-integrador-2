import type { Dayjs } from 'dayjs';
import generateCalendar from './generateCalendar';
export type { CalendarMode, CalendarProps, CalendarRef } from './generateCalendar';
declare const Calendar: import("react").ForwardRefExoticComponent<Readonly<import("./generateCalendar").CalendarProps<Dayjs>> & import("react").RefAttributes<import("./generateCalendar").CalendarRef>>;
export type CalendarType = typeof Calendar & {
    generateCalendar: typeof generateCalendar;
};
declare const _default: CalendarType;
export default _default;
