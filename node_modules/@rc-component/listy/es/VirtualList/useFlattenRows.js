import * as React from 'react';
import { toTaggedKey } from "../util";

// ============================== Types ===============================

/**
 * Flatten grouped data into header and item rows.
 * When grouping is enabled, items follow the insertion order of the group map
 * while preserving their original indexes.
 */
export default function useFlattenRows(data, groupData, getItemKey, group) {
  return React.useMemo(() => {
    // ============================== Init ================================
    const flatRows = [];
    const groupKeys = [];
    const groupKeyToItems = new Map();
    const itemRow = (item, index) => ({
      type: 'item',
      item,
      index,
      taggedKey: toTaggedKey(getItemKey(item), 'item')
    });

    // ============================ No Group ==============================
    if (!group) {
      data.forEach((item, index) => {
        flatRows.push(itemRow(item, index));
      });
      return {
        rows: flatRows,
        groupKeys,
        groupKeyToItems
      };
    }

    // ============================= Flatten ==============================
    groupData.forEach((groupItems, groupKey) => {
      groupKeyToItems.set(groupKey, groupItems.map(({
        item
      }) => item));
      groupKeys.push(groupKey);
      flatRows.push({
        type: 'group',
        groupKey,
        taggedKey: toTaggedKey(groupKey, 'group')
      });
      groupItems.forEach(({
        item,
        index
      }) => {
        flatRows.push(itemRow(item, index));
      });
    });

    // ============================== Return ==============================
    return {
      rows: flatRows,
      groupKeys,
      groupKeyToItems
    };
  }, [data, group, groupData, getItemKey]);
}