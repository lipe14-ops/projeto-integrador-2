import { useState } from 'react';
import { useEvent } from '@rc-component/util';
/**
 * @title multipleSelect hooks
 * @description multipleSelect by hold down shift key
 */
export const useMultipleSelect = getKey => {
  const [prevSelectedIndex, setPrevSelectedIndex] = useState(null);
  const multipleSelect = useEvent((currentSelectedIndex, data, selectedKeys) => {
    const configPrevSelectedIndex = prevSelectedIndex ?? currentSelectedIndex;
    // add/delete the selected range
    const startIndex = Math.min(configPrevSelectedIndex || 0, currentSelectedIndex);
    const endIndex = Math.max(configPrevSelectedIndex || 0, currentSelectedIndex);
    const rangeKeys = data.slice(startIndex, endIndex + 1).map(getKey);
    const shouldSelected = rangeKeys.some(rangeKey => !selectedKeys.has(rangeKey));
    const changedKeys = [];
    rangeKeys.forEach(item => {
      if (shouldSelected) {
        if (!selectedKeys.has(item)) {
          changedKeys.push(item);
        }
        selectedKeys.add(item);
      } else {
        selectedKeys.delete(item);
        changedKeys.push(item);
      }
    });
    setPrevSelectedIndex(shouldSelected ? endIndex : null);
    return changedKeys;
  });
  return [multipleSelect, setPrevSelectedIndex];
};