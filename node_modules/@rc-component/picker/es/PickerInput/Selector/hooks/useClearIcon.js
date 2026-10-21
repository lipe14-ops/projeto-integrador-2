import { isReactRenderable, warning } from '@rc-component/util';
import * as React from 'react';

/**
 * Used for `useFilledProps` since it already in the React.useMemo
 */
export function fillClearIcon(prefixCls, allowClear, clearIcon) {
  if (process.env.NODE_ENV !== 'production' && isReactRenderable(clearIcon)) {
    warning(false, '`clearIcon` will be removed in future. Please use `allowClear` instead.');
  }
  if (allowClear === false) {
    return null;
  }
  const config = allowClear && typeof allowClear === 'object' ? allowClear : {};
  if (isReactRenderable(config.clearIcon)) {
    return config.clearIcon;
  }
  return isReactRenderable(clearIcon) ? clearIcon : /*#__PURE__*/React.createElement("span", {
    className: `${prefixCls}-clear-btn`
  });
}