import React from 'react';
import { isNumber } from '../../_util/is';
import { isSameBorderWidth } from '../util';
const DEFAULT_BORDER_WIDTH = [0, 0, 0, 0];
const normalizeValue = val => {
  const size = Number.parseFloat(val);
  return isNumber(size) ? size : 0;
};
const useBorderSize = domNode => {
  const [borderWidth, setBorderWidth] = React.useState(DEFAULT_BORDER_WIDTH);
  React.useEffect(() => {
    if (!domNode) {
      setBorderWidth(prev => {
        if (isSameBorderWidth(prev, DEFAULT_BORDER_WIDTH)) {
          return prev;
        } else {
          return DEFAULT_BORDER_WIDTH;
        }
      });
      return;
    }
    const {
      borderTopWidth,
      borderRightWidth,
      borderBottomWidth,
      borderLeftWidth
    } = getComputedStyle(domNode);
    const nextBorderWidth = [normalizeValue(borderTopWidth), normalizeValue(borderRightWidth), normalizeValue(borderBottomWidth), normalizeValue(borderLeftWidth)];
    setBorderWidth(prev => {
      if (isSameBorderWidth(prev, nextBorderWidth)) {
        return prev;
      } else {
        return nextBorderWidth;
      }
    });
  }, [domNode]);
  return borderWidth;
};
export default useBorderSize;