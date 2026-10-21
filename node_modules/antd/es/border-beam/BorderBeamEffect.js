"use client";

import React from 'react';
import { createPortal } from 'react-dom';
import { clsx } from 'clsx';
import { isHTMLElement } from '../_util/is';
const BorderBeamEffectElement = props => {
  const {
    prefixCls,
    className,
    ...rest
  } = props;
  return /*#__PURE__*/React.createElement("div", {
    "aria-hidden": "true",
    className: clsx(prefixCls, className),
    ...rest
  });
};
const BorderBeamEffect = props => {
  const {
    prefixCls,
    hostDom,
    ...rest
  } = props;
  if (!hostDom || !isHTMLElement(hostDom)) {
    return null;
  }
  return /*#__PURE__*/createPortal(/*#__PURE__*/React.createElement(BorderBeamEffectElement, {
    prefixCls: prefixCls,
    ...rest
  }), hostDom);
};
export default BorderBeamEffect;