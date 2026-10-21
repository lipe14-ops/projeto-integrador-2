import * as React from 'react';
import type { ListComponentProps, ListyRef } from '../List';
export type RawListProps<T, K extends React.Key = React.Key> = ListComponentProps<T, K>;
declare const RawListWithRef: <T, K extends React.Key = React.Key>(props: RawListProps<T, K> & {
    ref?: React.Ref<ListyRef>;
}) => React.ReactElement;
export default RawListWithRef;
