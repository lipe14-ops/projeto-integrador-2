"use client";

import React, { useContext } from 'react';
import Button from '../../button/Button';
import { ModalContext } from '../context';
const NormalCancelBtn = () => {
  const {
    cancelButtonProps,
    cancelTextLocale,
    onCancel
  } = useContext(ModalContext);
  const onInternalClick = event => {
    onCancel?.(event);
    cancelButtonProps?.onClick?.(event);
  };
  return /*#__PURE__*/React.createElement(Button, {
    ...cancelButtonProps,
    onClick: onInternalClick
  }, cancelTextLocale);
};
export default NormalCancelBtn;