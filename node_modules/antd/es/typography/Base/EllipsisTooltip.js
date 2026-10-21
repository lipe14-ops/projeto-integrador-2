"use client";

import * as React from 'react';
import Tooltip from '../../tooltip';
const EllipsisTooltip = ({
  enableEllipsis,
  isEllipsis,
  disabled,
  children,
  tooltipProps
}) => {
  if (!tooltipProps?.title || !enableEllipsis) {
    return children;
  }
  return /*#__PURE__*/React.createElement(Tooltip, {
    ...tooltipProps,
    disabled: !isEllipsis || disabled
  }, children);
};
if (process.env.NODE_ENV !== 'production') {
  EllipsisTooltip.displayName = 'EllipsisTooltip';
}
export default EllipsisTooltip;