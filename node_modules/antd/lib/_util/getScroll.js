"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _is = require("./is");
const getScroll = target => {
  if (typeof window === 'undefined') {
    /* istanbul ignore next */
    return 0;
  }
  let result = 0;
  if ((0, _is.isWindow)(target)) {
    result = target.pageYOffset;
  } else if ((0, _is.isDocument)(target)) {
    result = target.documentElement.scrollTop;
  } else if ((0, _is.isHTMLElement)(target)) {
    result = target.scrollTop;
  } else if (target) {
    // According to the type inference, the `target` is `never` type.
    // Since we configured the loose mode type checking, and supports mocking the target with such shape below::
    //    `{ documentElement: { scrollLeft: 200, scrollTop: 400 } }`,
    //    the program may falls into this branch.
    // Check the corresponding tests for details. Don't sure what is the real scenario this happens.
    /* biome-ignore lint/complexity/useLiteralKeys: target is a never type */ /* eslint-disable-next-line dot-notation */
    result = target['scrollTop'];
  }
  if (target && !(0, _is.isWindow)(target) && !(0, _is.isNumber)(result)) {
    result = (target.ownerDocument ?? target).documentElement?.scrollTop;
  }
  return result;
};
var _default = exports.default = getScroll;