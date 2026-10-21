import * as React from 'react';
/** @deprecated Please use `GetProps<typeof Input.Group>` instead. */
export interface GroupProps {
    className?: string;
    size?: 'large' | 'small' | 'default';
    children?: React.ReactNode;
    style?: React.CSSProperties;
    onMouseEnter?: React.MouseEventHandler<HTMLSpanElement>;
    onMouseLeave?: React.MouseEventHandler<HTMLSpanElement>;
    onFocus?: React.FocusEventHandler<HTMLSpanElement>;
    onBlur?: React.FocusEventHandler<HTMLSpanElement>;
    prefixCls?: string;
    compact?: boolean;
}
export interface InputGroupProps extends GroupProps {
}
/** @deprecated Please use `Space.Compact` */
declare const Group: React.FC<InputGroupProps>;
export default Group;
