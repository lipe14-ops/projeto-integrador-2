"use client";

import * as React from 'react';
import { clsx } from 'clsx';
import { isPresetColor } from '../_util/colors';
import { useMergeSemantic, useSemanticRootStyle } from '../_util/hooks/useMergeSemantic';
import { useComponentConfig } from '../config-provider/context';
import useStyle from './style/ribbon';
const Ribbon = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    className,
    prefixCls: customizePrefixCls,
    style,
    color,
    children,
    text,
    placement = 'end',
    rootClassName,
    styles,
    classNames: ribbonClassNames
  } = props;
  const {
    getPrefixCls,
    direction,
    className: contextClassName,
    style: contextStyle,
    classNames: contextClassNames,
    styles: contextStyles
  } = useComponentConfig('ribbon');
  const prefixCls = getPrefixCls('ribbon', customizePrefixCls);
  const wrapperCls = `${prefixCls}-wrapper`;
  const [hashId, cssVarCls] = useStyle(prefixCls, wrapperCls);
  // =========== Merged Props for Semantic ===========
  const mergedProps = {
    ...props,
    placement
  };
  const contextIndicatorStyle = useSemanticRootStyle(contextStyle, 'indicator');
  const indicatorStyle = useSemanticRootStyle(style, 'indicator');
  const [mergedClassNames, mergedStyles] = useMergeSemantic([contextClassNames, ribbonClassNames], [contextStyles, contextIndicatorStyle, styles, indicatorStyle], {
    props: mergedProps
  });
  const colorInPreset = isPresetColor(color, false);
  const ribbonCls = clsx(prefixCls, `${prefixCls}-placement-${placement}`, {
    [`${prefixCls}-rtl`]: direction === 'rtl',
    [`${prefixCls}-color-${color}`]: colorInPreset
  }, className, contextClassName, mergedClassNames.indicator);
  const colorStyle = {};
  const cornerColorStyle = {};
  if (color && !colorInPreset) {
    colorStyle.background = color;
    cornerColorStyle.color = color;
  }
  const nativeElementRef = React.useRef(null);
  React.useImperativeHandle(ref, () => ({
    nativeElement: nativeElementRef.current
  }));
  return /*#__PURE__*/React.createElement("div", {
    ref: nativeElementRef,
    className: clsx(wrapperCls, rootClassName, hashId, cssVarCls, mergedClassNames.root),
    style: mergedStyles.root
  }, children, /*#__PURE__*/React.createElement("div", {
    className: clsx(ribbonCls, hashId),
    style: {
      ...colorStyle,
      ...mergedStyles.indicator
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: clsx(`${prefixCls}-content`, mergedClassNames.content),
    style: mergedStyles.content
  }, text), /*#__PURE__*/React.createElement("div", {
    className: `${prefixCls}-corner`,
    style: cornerColorStyle
  })));
});
if (process.env.NODE_ENV !== 'production') {
  Ribbon.displayName = 'Ribbon';
}
export default Ribbon;