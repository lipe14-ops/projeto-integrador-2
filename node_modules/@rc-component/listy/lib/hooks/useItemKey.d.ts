import type * as React from 'react';
import type { RowKey } from '../List';
export default function useItemKey<T>(rowKey: RowKey<T>): (item: T) => React.Key;
