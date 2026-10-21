import * as React from 'react';
import type { ListProps as VirtualListProps, ListRef as RcVirtualListRef } from '@rc-component/virtual-list';
import type { Group } from '../hooks/useGroupSegments';
type ExtraRenderInfo = Parameters<NonNullable<VirtualListProps<unknown>['extraRender']>>[0];
export interface StickyHeaderParams<T, K extends React.Key = React.Key> {
    enabled: boolean;
    group: Group<T, K> | undefined;
    groupKeys: K[];
    groupKeyToItems: Map<K, T[]>;
    prefixCls: string;
    listRef: React.RefObject<RcVirtualListRef | null>;
    headerClassName?: string;
    headerStyle?: React.CSSProperties;
}
export default function useStickyGroupHeader<T, K extends React.Key = React.Key>(params: StickyHeaderParams<T, K>): (info: ExtraRenderInfo) => React.JSX.Element;
export {};
