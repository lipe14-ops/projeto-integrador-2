"use strict";
"use client";

var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _clsx = require("clsx");
var _configProvider = require("../config-provider");
const CardGrid = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    prefixCls,
    className,
    hoverable = true,
    ...rest
  } = props;
  const {
    getPrefixCls
  } = React.useContext(_configProvider.ConfigContext);
  const prefix = getPrefixCls('card', prefixCls);
  const classString = (0, _clsx.clsx)(`${prefix}-grid`, className, {
    [`${prefix}-grid-hoverable`]: hoverable
  });
  const nativeElementRef = React.useRef(null);
  React.useImperativeHandle(ref, () => ({
    nativeElement: nativeElementRef.current
  }));
  return /*#__PURE__*/React.createElement("div", {
    ref: nativeElementRef,
    ...rest,
    className: classString
  });
});
if (process.env.NODE_ENV !== 'production') {
  CardGrid.displayName = 'CardGrid';
}
var _default = exports.default = CardGrid;