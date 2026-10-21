import * as React from 'react';
export interface Group<T, K extends React.Key = React.Key> {
    key: (item: T) => K;
    title: (groupKey: K, items: T[]) => React.ReactNode;
}
export interface GroupSegmentItem<T> {
    item: T;
    index: number;
}
/**
 * Build a lookup map from group key to all matching data items and their
 * original indexes.
 * This groups by key across the full data set and does not require items with
 * the same key to be contiguous.
 */
export default function useGroupSegments<T, K extends React.Key = React.Key>(data: T[], group?: Group<T, K>): Map<K, GroupSegmentItem<T>[]>;
