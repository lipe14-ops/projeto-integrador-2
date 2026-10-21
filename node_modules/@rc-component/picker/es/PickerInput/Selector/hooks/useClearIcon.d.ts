import type { ReactNode } from 'react';
import * as React from 'react';
/**
 * Used for `useFilledProps` since it already in the React.useMemo
 */
export declare function fillClearIcon(prefixCls: string, allowClear?: boolean | {
    clearIcon?: ReactNode;
}, clearIcon?: ReactNode): string | number | bigint | true | Iterable<ReactNode> | Promise<string | number | bigint | boolean | React.ReactPortal | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<ReactNode>> | React.JSX.Element;
