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
var _clsx = require("clsx");
var _getRenderPropValue = require("../_util/getRenderPropValue");
var _useMergeSemantic = require("../_util/hooks/useMergeSemantic");
var _motion = require("../_util/motion");
var _warning = require("../_util/warning");
var _context = require("../config-provider/context");
var _tooltip = _interopRequireDefault(require("../tooltip"));
var _useMergedArrow = _interopRequireDefault(require("../tooltip/hook/useMergedArrow"));
var _PurePanel = _interopRequireWildcard(require("./PurePanel"));
var _style = _interopRequireDefault(require("./style"));
// CSSINJS

const InternalPopover = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    prefixCls: customizePrefixCls,
    title,
    content,
    overlayClassName,
    placement = 'top',
    trigger,
    children,
    mouseEnterDelay,
    mouseLeaveDelay,
    onOpenChange,
    overlayStyle = {},
    styles,
    classNames,
    motion,
    arrow: popoverArrow,
    ...restProps
  } = props;
  const {
    getPrefixCls,
    className: contextClassName,
    style: contextStyle,
    classNames: contextClassNames,
    styles: contextStyles,
    arrow: contextArrow,
    trigger: contextTrigger,
    mouseEnterDelay: contextMouseEnterDelay,
    mouseLeaveDelay: contextMouseLeaveDelay
  } = (0, _context.useComponentConfig)('popover');
  const mergedMouseEnterDelay = mouseEnterDelay ?? contextMouseEnterDelay ?? 0.1;
  const mergedMouseLeaveDelay = mouseLeaveDelay ?? contextMouseLeaveDelay ?? 0.1;
  const prefixCls = getPrefixCls('popover', customizePrefixCls);
  const [hashId, cssVarCls] = (0, _style.default)(prefixCls);
  const rootPrefixCls = getPrefixCls();
  const mergedArrow = (0, _useMergedArrow.default)(popoverArrow, contextArrow);
  const mergedTrigger = trigger || contextTrigger || 'hover';
  // ========================== Warning ===========================
  if (process.env.NODE_ENV !== 'production') {
    const warning = (0, _warning.devUseWarning)('Popover');
    process.env.NODE_ENV !== "production" ? warning(!onOpenChange || onOpenChange.length <= 1, 'usage', 'The second `onOpenChange` parameter is internal and unsupported. Please lock to a previous version if needed.') : void 0;
  }
  // ============================= Styles =============================
  const mergedProps = {
    ...props,
    placement,
    trigger: mergedTrigger,
    mouseEnterDelay: mergedMouseEnterDelay,
    mouseLeaveDelay: mergedMouseLeaveDelay,
    overlayStyle,
    styles,
    classNames
  };
  const contextStyleRoot = (0, _useMergeSemantic.useSemanticRootStyle)(contextStyle);
  const overlayStyleRoot = (0, _useMergeSemantic.useSemanticRootStyle)(overlayStyle);
  const [mergedClassNames, mergedStyles] = (0, _useMergeSemantic.useMergeSemantic)([contextClassNames, classNames], [contextStyles, contextStyleRoot, styles, overlayStyleRoot], {
    props: mergedProps
  });
  const rootClassNames = (0, _clsx.clsx)(overlayClassName, hashId, cssVarCls, contextClassName, mergedClassNames.root);
  const [open, setOpen] = (0, _util.useControlledState)(props.defaultOpen ?? false, props.open);
  const settingOpen = nextOpen => {
    setOpen(nextOpen);
    onOpenChange?.(nextOpen);
  };
  const titleNode = (0, _getRenderPropValue.getRenderPropValue)(title);
  const contentNode = (0, _getRenderPropValue.getRenderPropValue)(content);
  return /*#__PURE__*/React.createElement(_tooltip.default, {
    unique: false,
    arrow: mergedArrow,
    placement: placement,
    trigger: mergedTrigger,
    mouseEnterDelay: mergedMouseEnterDelay,
    mouseLeaveDelay: mergedMouseLeaveDelay,
    ...restProps,
    prefixCls: prefixCls,
    classNames: {
      root: rootClassNames,
      container: mergedClassNames.container,
      arrow: mergedClassNames.arrow
    },
    styles: {
      root: mergedStyles.root,
      container: mergedStyles.container,
      arrow: mergedStyles.arrow
    },
    ref: ref,
    open: open,
    onOpenChange: settingOpen,
    overlay: (0, _util.isReactRenderable)(titleNode) || (0, _util.isReactRenderable)(contentNode) ? (/*#__PURE__*/React.createElement(_PurePanel.Overlay, {
      prefixCls: prefixCls,
      title: titleNode,
      content: contentNode,
      classNames: mergedClassNames,
      styles: mergedStyles
    })) : null,
    motion: {
      motionName: (0, _motion.getTransitionName)(rootPrefixCls, 'zoom-big', typeof motion?.motionName === 'string' ? motion?.motionName : undefined)
    },
    "data-popover-inject": true
  }, children);
});
const Popover = InternalPopover;
Popover._InternalPanelDoNotUseOrYouWillBeFired = _PurePanel.default;
if (process.env.NODE_ENV !== 'production') {
  Popover.displayName = 'Popover';
}
var _default = exports.default = Popover;