import * as React from 'react';
import type { ListComponentProps, ListyRef } from '../List';
export type VirtualListProps<T, K extends React.Key = React.Key> = ListComponentProps<T, K>;
declare const VirtualListWithRef: <T, K extends React.Key = React.Key>(props: VirtualListProps<T, K> & {
    ref?: React.Ref<ListyRef>;
}) => React.ReactElement;
export default VirtualListWithRef;
