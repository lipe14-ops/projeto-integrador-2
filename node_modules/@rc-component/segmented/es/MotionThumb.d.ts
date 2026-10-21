import * as React from 'react';
import type { SegmentedValue } from '.';
export interface MotionThumbInterface {
    containerRef: React.RefObject<HTMLDivElement | null>;
    value: SegmentedValue;
    getValueIndex: (value: SegmentedValue) => number;
    prefixCls: string;
    motionName: string;
    onMotionStart: VoidFunction;
    onMotionEnd: VoidFunction;
    direction?: 'ltr' | 'rtl';
    vertical?: boolean;
}
export default function MotionThumb(props: MotionThumbInterface): React.JSX.Element | null;
