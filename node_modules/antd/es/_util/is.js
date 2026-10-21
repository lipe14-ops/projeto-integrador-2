import { isNonNullable } from '@rc-component/util';
export const isNumber = val => {
  return typeof val === 'number' && !Number.isNaN(val);
};
export const isString = val => {
  return typeof val === 'string';
};
export const isPlainObject = val => {
  return val !== null && typeof val === 'object';
};
export const isFunction = val => {
  return typeof val === 'function';
};
export const isThenable = val => {
  return isNonNullable(val) && isFunction(val.then);
};
export const isPrimitive = val => {
  return typeof val !== 'object' && !isFunction(val) || val === null;
};
export const isTransitionEvent = event => {
  return isPlainObject(event) && 'propertyName' in event && isString(event.propertyName);
};
export const isWindow = val => {
  if (!isNonNullable(val)) {
    return false;
  }
  return val === val.window;
};
export const isDocument = val => {
  if (!isNonNullable(val)) {
    return false;
  }
  return val instanceof Document || val.constructor.name === 'HTMLDocument' || val.nodeType === window.Node.DOCUMENT_NODE;
};
export const isHTMLElement = val => {
  if (!isNonNullable(val)) {
    return false;
  }
  return typeof HTMLElement !== 'undefined' && val instanceof HTMLElement;
};