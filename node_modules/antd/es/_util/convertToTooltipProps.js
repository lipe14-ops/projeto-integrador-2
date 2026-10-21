import { isValidElement } from 'react';
import { isReactRenderable } from '@rc-component/util';
import { isPlainObject } from './is';
const convertToTooltipProps = (tooltip, context) => {
  if (!isReactRenderable(tooltip)) {
    return null;
  }
  if (isPlainObject(tooltip) && ! /*#__PURE__*/isValidElement(tooltip)) {
    return {
      ...context,
      ...tooltip
    };
  }
  return {
    ...context,
    title: tooltip
  };
};
export default convertToTooltipProps;