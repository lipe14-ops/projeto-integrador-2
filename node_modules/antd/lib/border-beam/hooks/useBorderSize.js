"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireDefault(require("react"));
var _is = require("../../_util/is");
var _util = require("../util");
const DEFAULT_BORDER_WIDTH = [0, 0, 0, 0];
const normalizeValue = val => {
  const size = Number.parseFloat(val);
  return (0, _is.isNumber)(size) ? size : 0;
};
const useBorderSize = domNode => {
  const [borderWidth, setBorderWidth] = _react.default.useState(DEFAULT_BORDER_WIDTH);
  _react.default.useEffect(() => {
    if (!domNode) {
      setBorderWidth(prev => {
        if ((0, _util.isSameBorderWidth)(prev, DEFAULT_BORDER_WIDTH)) {
          return prev;
        } else {
          return DEFAULT_BORDER_WIDTH;
        }
      });
      return;
    }
    const {
      borderTopWidth,
      borderRightWidth,
      borderBottomWidth,
      borderLeftWidth
    } = getComputedStyle(domNode);
    const nextBorderWidth = [normalizeValue(borderTopWidth), normalizeValue(borderRightWidth), normalizeValue(borderBottomWidth), normalizeValue(borderLeftWidth)];
    setBorderWidth(prev => {
      if ((0, _util.isSameBorderWidth)(prev, nextBorderWidth)) {
        return prev;
      } else {
        return nextBorderWidth;
      }
    });
  }, [domNode]);
  return borderWidth;
};
var _default = exports.default = useBorderSize;