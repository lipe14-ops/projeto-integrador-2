import React from 'react';
import { isReactRenderable } from '@rc-component/util';
export function getClearIcon(prefixCls, allowClear, clearIcon) {
  const mergedClearIcon = typeof allowClear === 'object' ? allowClear.clearIcon : clearIcon;
  return isReactRenderable(mergedClearIcon) ? mergedClearIcon : /*#__PURE__*/React.createElement("span", {
    className: `${prefixCls}-clear-btn`
  });
}