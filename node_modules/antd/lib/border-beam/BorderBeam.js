"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var _cssinjs = require("@ant-design/cssinjs");
var _util = require("@rc-component/util");
var _clsx = require("clsx");
var _is = require("../_util/is");
var _context = require("../config-provider/context");
var _genStyleUtils = require("../theme/util/genStyleUtils");
var _BorderBeamEffect = _interopRequireDefault(require("./BorderBeamEffect"));
var _useBorderSize = _interopRequireDefault(require("./hooks/useBorderSize"));
var _useChildDom = _interopRequireDefault(require("./hooks/useChildDom"));
var _style = _interopRequireDefault(require("./style"));
var _util2 = require("./util");
const getInset = width => {
  return (0, _is.isString)(width) ? `calc(-1 * ${width})` : `-${width}px`;
};
const BorderBeam = props => {
  const {
    prefixCls: customizePrefixCls,
    className,
    style,
    children,
    color,
    count = 1,
    duration,
    lineWidth,
    outset,
    size
  } = props;
  const {
    className: contextClassName,
    style: contextStyle,
    getPrefixCls
  } = (0, _context.useComponentConfig)('borderBeam');
  // ============================ Prefix ============================
  const prefixCls = getPrefixCls('border-beam', customizePrefixCls);
  const [hashId, cssVarCls] = (0, _style.default)(prefixCls);
  const [varName] = (0, _genStyleUtils.genCssVar)(getPrefixCls(), 'border-beam');
  // ============================= Host =============================
  const [childNode, childDomNode] = (0, _useChildDom.default)(children);
  const borderWidth = (0, _useBorderSize.default)(childDomNode);
  const beamGradient = (0, _react.useMemo)(() => (0, _util2.getBorderBeamGradient)(color), [color]);
  const mergedCount = (0, _is.isNumber)(count) && Number.isFinite(count) && count >= 1 ? Math.floor(count) : 1;
  const mergedDuration = (0, _is.isNumber)(duration) && duration > 0 ? duration : _util2.DEFAULT_BORDER_BEAM_DURATION;
  // ============================ Border ============================
  const insetOffset = (0, _react.useMemo)(() => {
    return (0, _util.isNonNullable)(outset) ? getInset(outset) : borderWidth.map(getInset).join(' ');
  }, [borderWidth, outset]);
  // ============================ Render ============================
  return /*#__PURE__*/_react.default.createElement(_react.default.Fragment, null, childNode, Array.from({
    length: mergedCount
  }, (_, index) => (/*#__PURE__*/_react.default.createElement(_BorderBeamEffect.default, {
    key: index,
    prefixCls: prefixCls,
    hostDom: childDomNode,
    className: (0, _clsx.clsx)(contextClassName, className, hashId, cssVarCls),
    style: {
      ...contextStyle,
      ...style,
      ...(beamGradient && {
        [varName('beam-gradient')]: beamGradient
      }),
      ...((0, _is.isNumber)(duration) && duration > 0 && {
        [varName('duration')]: `${duration}s`
      }),
      ...((0, _util.isNonNullable)(lineWidth) && {
        [varName('line-width')]: (0, _cssinjs.unit)(lineWidth)
      }),
      ...((0, _util.isNonNullable)(size) && {
        [varName('size')]: (0, _cssinjs.unit)(size)
      }),
      ...(index > 0 && {
        [varName('delay')]: `${-mergedDuration * index / mergedCount}s`
      }),
      [varName('inset-offset')]: insetOffset
    }
  }))));
};
if (process.env.NODE_ENV !== 'production') {
  BorderBeam.displayName = 'BorderBeam';
}
var _default = exports.default = BorderBeam;