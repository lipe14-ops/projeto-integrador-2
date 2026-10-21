import React from 'react';
import type { FloatButtonElement, FloatButtonProps, FloatButtonRef } from './FloatButton';
/** @deprecated Please use `GetProps<typeof FloatButton.BackTop>` instead. */
export interface BackTopProps extends Omit<FloatButtonProps, 'target'> {
    visibilityHeight?: number;
    onClick?: React.MouseEventHandler<FloatButtonElement>;
    target?: () => HTMLElement | Window | Document;
    prefixCls?: string;
    children?: React.ReactNode;
    className?: string;
    rootClassName?: string;
    style?: React.CSSProperties;
    duration?: number;
    /**
     * @since 6.6.0
     * @default false
     */
    showProgress?: boolean;
}
export interface FloatButtonBackTopProps extends BackTopProps {
}
declare const BackTop: React.ForwardRefExoticComponent<FloatButtonBackTopProps & React.RefAttributes<FloatButtonRef>>;
export default BackTop;
