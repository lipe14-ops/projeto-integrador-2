"use client";

import * as React from 'react';
import { clsx } from 'clsx';
import { ConfigContext } from '../config-provider';
const CardGrid = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    prefixCls,
    className,
    hoverable = true,
    ...rest
  } = props;
  const {
    getPrefixCls
  } = React.useContext(ConfigContext);
  const prefix = getPrefixCls('card', prefixCls);
  const classString = clsx(`${prefix}-grid`, className, {
    [`${prefix}-grid-hoverable`]: hoverable
  });
  const nativeElementRef = React.useRef(null);
  React.useImperativeHandle(ref, () => ({
    nativeElement: nativeElementRef.current
  }));
  return /*#__PURE__*/React.createElement("div", {
    ref: nativeElementRef,
    ...rest,
    className: classString
  });
});
if (process.env.NODE_ENV !== 'production') {
  CardGrid.displayName = 'CardGrid';
}
export default CardGrid;