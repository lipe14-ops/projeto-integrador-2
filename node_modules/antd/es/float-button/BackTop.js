"use client";

import React, { useContext } from 'react';
import VerticalAlignTopOutlined from "@ant-design/icons/es/icons/VerticalAlignTopOutlined";
import CSSMotion from '@rc-component/motion';
import { composeRef } from '@rc-component/util';
import { clsx } from 'clsx';
import scrollTo from '../_util/scrollTo';
import { ConfigContext } from '../config-provider';
import { useComponentConfig } from '../config-provider/context';
import { genCssVar } from '../theme/util/genStyleUtils';
import { GroupContext } from './context';
import FloatButton, { floatButtonPrefixCls } from './FloatButton';
import useScroll from './hooks/useScroll';
const defaultIcon = /*#__PURE__*/React.createElement(VerticalAlignTopOutlined, null);
const BackTop = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    backTopIcon: contextIcon
  } = useComponentConfig('floatButton');
  const {
    prefixCls: customizePrefixCls,
    className,
    style,
    type = 'default',
    shape = 'circle',
    visibilityHeight = 400,
    icon,
    target,
    onClick,
    duration = 450,
    showProgress = false,
    ...restProps
  } = props;
  const mergedIcon = icon ?? contextIcon ?? defaultIcon;
  const internalRef = React.useRef(null);
  React.useImperativeHandle(ref, () => ({
    nativeElement: internalRef.current
  }));
  const getDefaultTarget = React.useCallback(() => {
    return internalRef.current?.ownerDocument || window;
  }, []);
  const getTarget = target || getDefaultTarget;
  const {
    scrollProgress,
    visible
  } = useScroll({
    getTarget,
    showProgress,
    visibilityHeight
  });
  const scrollToTop = e => {
    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    scrollTo(0, {
      getContainer: getTarget,
      duration: prefersReducedMotion?.matches ? 0 : duration
    });
    onClick?.(e);
  };
  const {
    getPrefixCls
  } = useContext(ConfigContext);
  const prefixCls = getPrefixCls(floatButtonPrefixCls, customizePrefixCls);
  const rootPrefixCls = getPrefixCls();
  const [varName] = genCssVar(rootPrefixCls, 'float-btn');
  const groupShape = useContext(GroupContext)?.shape;
  const mergedShape = groupShape || shape;
  const contentProps = {
    prefixCls,
    icon: mergedIcon,
    type,
    shape: mergedShape,
    style: showProgress ? {
      [varName('progress')]: `${scrollProgress}turn`,
      ...style
    } : style,
    ...restProps
  };
  return /*#__PURE__*/React.createElement(CSSMotion, {
    visible: visible,
    motionName: `${rootPrefixCls}-fade`
  }, ({
    className: motionClassName
  }, setRef) => (/*#__PURE__*/React.createElement(FloatButton, {
    ref: composeRef(internalRef, setRef),
    ...contentProps,
    onClick: scrollToTop,
    className: clsx(className, motionClassName, {
      [`${prefixCls}-progress`]: showProgress
    })
  })));
});
if (process.env.NODE_ENV !== 'production') {
  BackTop.displayName = 'FloatButton.BackTop';
}
export default BackTop;