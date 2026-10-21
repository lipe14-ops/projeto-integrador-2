import * as React from 'react';
import type { Group, GroupSegmentItem } from '../hooks/useGroupSegments';
export type Row<T, K extends React.Key = React.Key> = ({
    type: 'group';
    groupKey: K;
} | {
    type: 'item';
    item: T;
    index: number;
}) & {
    taggedKey: string;
};
export interface FlattenRowsResult<T, K extends React.Key = React.Key> {
    rows: Row<T, K>[];
    groupKeys: K[];
    groupKeyToItems: Map<K, T[]>;
}
/**
 * Flatten grouped data into header and item rows.
 * When grouping is enabled, items follow the insertion order of the group map
 * while preserving their original indexes.
 */
export default function useFlattenRows<T, K extends React.Key = React.Key>(data: T[], groupData: Map<K, GroupSegmentItem<T>[]>, getItemKey: (item: T) => React.Key, group?: Group<T, K>): FlattenRowsResult<T, K>;
