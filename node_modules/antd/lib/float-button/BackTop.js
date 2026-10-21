"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var _VerticalAlignTopOutlined = _interopRequireDefault(require("@ant-design/icons/VerticalAlignTopOutlined"));
var _motion = _interopRequireDefault(require("@rc-component/motion"));
var _util = require("@rc-component/util");
var _clsx = require("clsx");
var _scrollTo = _interopRequireDefault(require("../_util/scrollTo"));
var _configProvider = require("../config-provider");
var _context = require("../config-provider/context");
var _genStyleUtils = require("../theme/util/genStyleUtils");
var _context2 = require("./context");
var _FloatButton = _interopRequireWildcard(require("./FloatButton"));
var _useScroll = _interopRequireDefault(require("./hooks/useScroll"));
const defaultIcon = /*#__PURE__*/_react.default.createElement(_VerticalAlignTopOutlined.default, null);
const BackTop = /*#__PURE__*/_react.default.forwardRef((props, ref) => {
  const {
    backTopIcon: contextIcon
  } = (0, _context.useComponentConfig)('floatButton');
  const {
    prefixCls: customizePrefixCls,
    className,
    style,
    type = 'default',
    shape = 'circle',
    visibilityHeight = 400,
    icon,
    target,
    onClick,
    duration = 450,
    showProgress = false,
    ...restProps
  } = props;
  const mergedIcon = icon ?? contextIcon ?? defaultIcon;
  const internalRef = _react.default.useRef(null);
  _react.default.useImperativeHandle(ref, () => ({
    nativeElement: internalRef.current
  }));
  const getDefaultTarget = _react.default.useCallback(() => {
    return internalRef.current?.ownerDocument || window;
  }, []);
  const getTarget = target || getDefaultTarget;
  const {
    scrollProgress,
    visible
  } = (0, _useScroll.default)({
    getTarget,
    showProgress,
    visibilityHeight
  });
  const scrollToTop = e => {
    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    (0, _scrollTo.default)(0, {
      getContainer: getTarget,
      duration: prefersReducedMotion?.matches ? 0 : duration
    });
    onClick?.(e);
  };
  const {
    getPrefixCls
  } = (0, _react.useContext)(_configProvider.ConfigContext);
  const prefixCls = getPrefixCls(_FloatButton.floatButtonPrefixCls, customizePrefixCls);
  const rootPrefixCls = getPrefixCls();
  const [varName] = (0, _genStyleUtils.genCssVar)(rootPrefixCls, 'float-btn');
  const groupShape = (0, _react.useContext)(_context2.GroupContext)?.shape;
  const mergedShape = groupShape || shape;
  const contentProps = {
    prefixCls,
    icon: mergedIcon,
    type,
    shape: mergedShape,
    style: showProgress ? {
      [varName('progress')]: `${scrollProgress}turn`,
      ...style
    } : style,
    ...restProps
  };
  return /*#__PURE__*/_react.default.createElement(_motion.default, {
    visible: visible,
    motionName: `${rootPrefixCls}-fade`
  }, ({
    className: motionClassName
  }, setRef) => (/*#__PURE__*/_react.default.createElement(_FloatButton.default, {
    ref: (0, _util.composeRef)(internalRef, setRef),
    ...contentProps,
    onClick: scrollToTop,
    className: (0, _clsx.clsx)(className, motionClassName, {
      [`${prefixCls}-progress`]: showProgress
    })
  })));
});
if (process.env.NODE_ENV !== 'production') {
  BackTop.displayName = 'FloatButton.BackTop';
}
var _default = exports.default = BackTop;