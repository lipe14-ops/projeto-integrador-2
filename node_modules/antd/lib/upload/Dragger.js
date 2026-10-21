"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _util = require("@rc-component/util");
var _Upload = _interopRequireDefault(require("./Upload"));
const Dragger = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    style,
    height,
    hasControlInside = false,
    children,
    ...restProps
  } = props;
  const mergedStyle = {
    ...style,
    ...((0, _util.isNonNullable)(height) && {
      height
    })
  };
  return /*#__PURE__*/React.createElement(_Upload.default, {
    ref: ref,
    hasControlInside: hasControlInside,
    ...restProps,
    style: mergedStyle,
    type: "drag"
  }, children);
});
if (process.env.NODE_ENV !== 'production') {
  Dragger.displayName = 'Dragger';
}
var _default = exports.default = Dragger;