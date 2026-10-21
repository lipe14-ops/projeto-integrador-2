"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var _Button = _interopRequireDefault(require("../../button/Button"));
var _context = require("../context");
const NormalCancelBtn = () => {
  const {
    cancelButtonProps,
    cancelTextLocale,
    onCancel
  } = (0, _react.useContext)(_context.ModalContext);
  const onInternalClick = event => {
    onCancel?.(event);
    cancelButtonProps?.onClick?.(event);
  };
  return /*#__PURE__*/_react.default.createElement(_Button.default, {
    ...cancelButtonProps,
    onClick: onInternalClick
  }, cancelTextLocale);
};
var _default = exports.default = NormalCancelBtn;