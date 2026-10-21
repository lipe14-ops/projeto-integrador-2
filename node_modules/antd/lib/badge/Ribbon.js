"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _clsx = require("clsx");
var _colors = require("../_util/colors");
var _useMergeSemantic = require("../_util/hooks/useMergeSemantic");
var _context = require("../config-provider/context");
var _ribbon = _interopRequireDefault(require("./style/ribbon"));
const Ribbon = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    className,
    prefixCls: customizePrefixCls,
    style,
    color,
    children,
    text,
    placement = 'end',
    rootClassName,
    styles,
    classNames: ribbonClassNames
  } = props;
  const {
    getPrefixCls,
    direction,
    className: contextClassName,
    style: contextStyle,
    classNames: contextClassNames,
    styles: contextStyles
  } = (0, _context.useComponentConfig)('ribbon');
  const prefixCls = getPrefixCls('ribbon', customizePrefixCls);
  const wrapperCls = `${prefixCls}-wrapper`;
  const [hashId, cssVarCls] = (0, _ribbon.default)(prefixCls, wrapperCls);
  // =========== Merged Props for Semantic ===========
  const mergedProps = {
    ...props,
    placement
  };
  const contextIndicatorStyle = (0, _useMergeSemantic.useSemanticRootStyle)(contextStyle, 'indicator');
  const indicatorStyle = (0, _useMergeSemantic.useSemanticRootStyle)(style, 'indicator');
  const [mergedClassNames, mergedStyles] = (0, _useMergeSemantic.useMergeSemantic)([contextClassNames, ribbonClassNames], [contextStyles, contextIndicatorStyle, styles, indicatorStyle], {
    props: mergedProps
  });
  const colorInPreset = (0, _colors.isPresetColor)(color, false);
  const ribbonCls = (0, _clsx.clsx)(prefixCls, `${prefixCls}-placement-${placement}`, {
    [`${prefixCls}-rtl`]: direction === 'rtl',
    [`${prefixCls}-color-${color}`]: colorInPreset
  }, className, contextClassName, mergedClassNames.indicator);
  const colorStyle = {};
  const cornerColorStyle = {};
  if (color && !colorInPreset) {
    colorStyle.background = color;
    cornerColorStyle.color = color;
  }
  const nativeElementRef = React.useRef(null);
  React.useImperativeHandle(ref, () => ({
    nativeElement: nativeElementRef.current
  }));
  return /*#__PURE__*/React.createElement("div", {
    ref: nativeElementRef,
    className: (0, _clsx.clsx)(wrapperCls, rootClassName, hashId, cssVarCls, mergedClassNames.root),
    style: mergedStyles.root
  }, children, /*#__PURE__*/React.createElement("div", {
    className: (0, _clsx.clsx)(ribbonCls, hashId),
    style: {
      ...colorStyle,
      ...mergedStyles.indicator
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: (0, _clsx.clsx)(`${prefixCls}-content`, mergedClassNames.content),
    style: mergedStyles.content
  }, text), /*#__PURE__*/React.createElement("div", {
    className: `${prefixCls}-corner`,
    style: cornerColorStyle
  })));
});
if (process.env.NODE_ENV !== 'production') {
  Ribbon.displayName = 'Ribbon';
}
var _default = exports.default = Ribbon;