"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.getClearIcon = getClearIcon;
var _react = _interopRequireDefault(require("react"));
var _util = require("@rc-component/util");
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function getClearIcon(prefixCls, allowClear, clearIcon) {
  const mergedClearIcon = typeof allowClear === 'object' ? allowClear.clearIcon : clearIcon;
  return (0, _util.isReactRenderable)(mergedClearIcon) ? mergedClearIcon : /*#__PURE__*/_react.default.createElement("span", {
    className: `${prefixCls}-clear-btn`
  });
}