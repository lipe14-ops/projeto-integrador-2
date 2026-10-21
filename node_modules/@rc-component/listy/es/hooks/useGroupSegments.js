import * as React from 'react';

// ============================== Types ===============================

/**
 * Build a lookup map from group key to all matching data items and their
 * original indexes.
 * This groups by key across the full data set and does not require items with
 * the same key to be contiguous.
 */
export default function useGroupSegments(data, group) {
  return React.useMemo(() => {
    // ============================== Init ================================
    const map = new Map();

    // ============================ No Group ==============================
    if (!group) {
      return map;
    }

    // ============================= Collect ==============================
    data.forEach((item, index) => {
      const groupKey = group.key(item);
      const groupItems = map.get(groupKey);
      const groupSegmentItem = {
        item,
        index
      };
      if (groupItems) {
        groupItems.push(groupSegmentItem);
      } else {
        map.set(groupKey, [groupSegmentItem]);
      }
    });

    // ============================== Return ==============================
    return map;
  }, [data, group]);
}