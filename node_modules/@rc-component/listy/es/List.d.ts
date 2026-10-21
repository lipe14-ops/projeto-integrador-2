import * as React from 'react';
import type { Group } from './hooks/useGroupSegments';
export type RowKey<T> = keyof T | ((item: T) => React.Key);
export type ScrollAlign = 'top' | 'bottom' | 'auto';
export type ListySemanticName = 'root' | 'item' | 'groupHeader';
export type ListyClassNames = Partial<Record<ListySemanticName, string>>;
export type ListyStyles = Partial<Record<ListySemanticName, React.CSSProperties>>;
export interface GroupScrollToConfig {
    groupKey: React.Key;
    align?: ScrollAlign;
    offset?: number;
}
export interface KeyScrollToConfig {
    key: React.Key;
    align?: ScrollAlign;
    offset?: number;
}
export interface PositionScrollToConfig {
    left?: number;
    top?: number;
}
export type ListyScrollToConfig = number | null | KeyScrollToConfig | PositionScrollToConfig | GroupScrollToConfig;
export interface ListyRef {
    scrollTo: (config?: ListyScrollToConfig) => void;
}
export interface ListyProps<T, K extends React.Key = React.Key> {
    items?: T[];
    sticky?: boolean;
    itemHeight?: number;
    height?: number;
    group?: Group<T, K>;
    virtual?: boolean;
    direction?: 'ltr' | 'rtl';
    prefixCls?: string;
    rowKey: RowKey<T>;
    classNames?: ListyClassNames;
    styles?: ListyStyles;
    onScroll?: React.UIEventHandler<HTMLElement>;
    itemRender: (item: T, index: number) => React.ReactNode;
}
export interface ListComponentProps<T, K extends React.Key = React.Key> {
    data: T[];
    sticky?: boolean;
    itemHeight?: number;
    height?: number;
    group?: Group<T, K>;
    direction?: 'ltr' | 'rtl';
    prefixCls: string;
    rowKey: RowKey<T>;
    classNames?: ListyClassNames;
    styles?: ListyStyles;
    onScroll?: React.UIEventHandler<HTMLElement>;
    itemRender: (item: T, index: number) => React.ReactNode;
}
declare const ListyWithForwardRef: <T, K extends React.Key = React.Key>(props: ListyProps<T, K> & {
    ref?: React.Ref<ListyRef>;
}) => React.ReactElement;
export default ListyWithForwardRef;
