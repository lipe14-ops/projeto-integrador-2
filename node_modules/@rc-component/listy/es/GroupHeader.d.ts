import * as React from 'react';
import type { Group } from './hooks/useGroupSegments';
export interface GroupHeaderProps<T, K extends React.Key = React.Key> {
    group: Group<T, K>;
    groupKey: K;
    groupItems: T[];
    prefixCls: string;
    fixed?: boolean;
    sticky?: boolean;
    className?: string;
    style?: React.CSSProperties;
}
declare const GroupHeaderWithRef: <T, K extends React.Key = React.Key>(props: GroupHeaderProps<T, K> & {
    ref?: React.Ref<HTMLDivElement>;
}) => React.ReactElement;
export default GroupHeaderWithRef;
