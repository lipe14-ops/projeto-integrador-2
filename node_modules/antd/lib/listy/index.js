"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireDefault(require("react"));
var _listy = _interopRequireDefault(require("@rc-component/listy"));
var _clsx = require("clsx");
var _useMergeSemantic = require("../_util/hooks/useMergeSemantic");
var _context = require("../config-provider/context");
var _useCSSVarCls = _interopRequireDefault(require("../config-provider/hooks/useCSSVarCls"));
var _internal = require("../theme/internal");
var _style = _interopRequireDefault(require("./style"));
const InternalListy = (props, ref) => {
  const {
    prefixCls: customizePrefixCls,
    rootClassName,
    className,
    style,
    classNames,
    styles,
    virtual,
    ...restProps
  } = props;
  const {
    getPrefixCls,
    direction,
    className: contextClassName,
    style: contextStyle,
    classNames: contextClassNames,
    styles: contextStyles
  } = (0, _context.useComponentConfig)('listy');
  const {
    virtual: contextVirtual
  } = _react.default.useContext(_context.ConfigContext);
  const prefixCls = getPrefixCls('listy', customizePrefixCls);
  const rootCls = (0, _useCSSVarCls.default)(prefixCls);
  const [hashId, cssVarCls] = (0, _style.default)(prefixCls, rootCls);
  const [, token] = (0, _internal.useToken)();
  const listyToken = {
    ...token,
    ...token.Listy
  };
  const itemHeight = listyToken.fontHeight + (listyToken.itemPaddingBlock ?? listyToken.paddingSM) * 2;
  const contextStyleRoot = (0, _useMergeSemantic.useSemanticRootStyle)(contextStyle);
  const styleRoot = (0, _useMergeSemantic.useSemanticRootStyle)(style);
  const [mergedClassNames, mergedStyles] = (0, _useMergeSemantic.useMergeSemantic)([contextClassNames, classNames], [contextStyles, contextStyleRoot, styles, styleRoot], {
    props: props
  });
  const rootClassNames = (0, _clsx.clsx)(contextClassName, mergedClassNames.root, rootClassName, className, hashId, cssVarCls, rootCls);
  const mergedVirtual = virtual ?? contextVirtual ?? false;
  return /*#__PURE__*/_react.default.createElement(_listy.default, {
    ...restProps,
    ref: ref,
    prefixCls: prefixCls,
    direction: direction,
    virtual: mergedVirtual,
    itemHeight: itemHeight,
    classNames: {
      ...mergedClassNames,
      root: rootClassNames
    },
    styles: mergedStyles
  });
};
const Listy = /*#__PURE__*/_react.default.forwardRef(InternalListy);
if (process.env.NODE_ENV !== 'production') {
  Listy.displayName = 'Listy';
}
var _default = exports.default = Listy;