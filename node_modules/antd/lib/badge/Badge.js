"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _motion = _interopRequireDefault(require("@rc-component/motion"));
var _util = require("@rc-component/util");
var _clsx = require("clsx");
var _colors = require("../_util/colors");
var _useMergeSemantic = require("../_util/hooks/useMergeSemantic");
var _is = require("../_util/is");
var _reactNode = require("../_util/reactNode");
var _warning = require("../_util/warning");
var _context = require("../config-provider/context");
var _ScrollNumber = _interopRequireDefault(require("./ScrollNumber"));
var _style = _interopRequireDefault(require("./style"));
const Badge = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    prefixCls: customizePrefixCls,
    scrollNumberPrefixCls: customizeScrollNumberPrefixCls,
    children,
    status,
    text,
    color,
    count = null,
    overflowCount = 99,
    dot = false,
    size = 'medium',
    title,
    offset,
    style,
    className,
    rootClassName,
    classNames,
    styles,
    showZero = false,
    ...restProps
  } = props;
  const {
    getPrefixCls,
    direction,
    className: contextClassName,
    style: contextStyle,
    classNames: contextClassNames,
    styles: contextStyles
  } = (0, _context.useComponentConfig)('badge');
  const prefixCls = getPrefixCls('badge', customizePrefixCls);
  const [hashId, cssVarCls] = (0, _style.default)(prefixCls);
  if (process.env.NODE_ENV !== 'production') {
    const warning = (0, _warning.devUseWarning)('Badge');
    warning.deprecated(size !== 'default', 'size="default"', 'size="medium"');
  }
  // =========== Merged Props for Semantic ===========
  const mergedProps = {
    ...props,
    overflowCount,
    size,
    dot,
    showZero
  };
  // ================================ Misc ================================
  const numberedDisplayCount = count > overflowCount ? `${overflowCount}+` : count;
  const isZero = numberedDisplayCount === '0' || numberedDisplayCount === 0 || text === '0' || text === 0;
  const ignoreCount = count === null || isZero && !showZero;
  const hasStatus = ((0, _util.isNonNullable)(status) || (0, _util.isNonNullable)(color)) && ignoreCount;
  const hasStatusValue = (0, _util.isNonNullable)(status) || !isZero;
  const isStatusBadge = Boolean(!children && hasStatus && (text || hasStatusValue || !ignoreCount));
  // =============================== Styles ===============================
  const offsetStyle = (0, _react.useMemo)(() => {
    if (!offset) {
      return undefined;
    }
    const horizontalOffset = Number.parseInt(offset[0], 10);
    return {
      marginTop: offset[1],
      insetInlineEnd: -horizontalOffset
    };
  }, [offset]);
  const mergedStyle = (0, _react.useMemo)(() => ({
    ...offsetStyle,
    ...contextStyle,
    ...style
  }), [offsetStyle, style, contextStyle]);
  const legacyStyleKey = isStatusBadge ? 'root' : 'indicator';
  const contextLegacyStyle = (0, _useMergeSemantic.useSemanticRootStyle)(contextStyle, legacyStyleKey);
  const componentLegacyStyle = (0, _useMergeSemantic.useSemanticRootStyle)(style, legacyStyleKey);
  const [mergedClassNames, mergedStyles] = (0, _useMergeSemantic.useMergeSemantic)([contextClassNames, classNames], [contextStyles, contextLegacyStyle, styles, componentLegacyStyle], {
    props: mergedProps
  });
  const showAsDot = dot && !isZero;
  const mergedCount = showAsDot ? '' : numberedDisplayCount;
  const isHidden = (0, _react.useMemo)(() => {
    const isEmpty = !(0, _util.isReactRenderable)(mergedCount) && !(0, _util.isReactRenderable)(text);
    return (isEmpty || isZero && !showZero) && !showAsDot;
  }, [mergedCount, isZero, showZero, showAsDot, text]);
  // Count should be cache in case hidden change it
  const countRef = (0, _react.useRef)(count);
  if (!isHidden) {
    countRef.current = count;
  }
  const livingCount = countRef.current;
  // We need cache count since remove motion should not change count display
  const displayCountRef = (0, _react.useRef)(mergedCount);
  if (!isHidden) {
    displayCountRef.current = mergedCount;
  }
  const displayCount = displayCountRef.current;
  // We will cache the dot status to avoid shaking on leaved motion
  const isDotRef = (0, _react.useRef)(showAsDot);
  if (!isHidden) {
    isDotRef.current = showAsDot;
  }
  // =============================== Render ===============================
  // >>> Title
  const fallbackTitleNode = (0, _is.isString)(livingCount) || (0, _is.isNumber)(livingCount) ? livingCount : undefined;
  const titleNode = title === null || title === false ? undefined : title ?? fallbackTitleNode;
  // >>> Status Text
  const showStatusTextNode = !isHidden && (text === 0 ? showZero : !!text && text !== true);
  const statusTextNode = !showStatusTextNode ? null : (/*#__PURE__*/React.createElement("span", {
    className: `${prefixCls}-status-text`
  }, text));
  // >>> Display Component
  const displayNode = (0, _is.isPlainObject)(livingCount) ? (0, _reactNode.cloneElement)(livingCount, oriProps => ({
    style: {
      ...mergedStyle,
      ...oriProps.style
    }
  })) : undefined;
  // InternalColor
  const isInternalColor = (0, _colors.isPresetColor)(color, false);
  // Shared styles
  const statusCls = (0, _clsx.clsx)(mergedClassNames.indicator, {
    [`${prefixCls}-status-dot`]: hasStatus,
    [`${prefixCls}-status-${status}`]: !!status,
    [`${prefixCls}-color-${color}`]: isInternalColor
  });
  const statusStyle = {};
  if (color && !isInternalColor) {
    statusStyle.color = color;
    statusStyle.background = color;
  }
  const badgeClassName = (0, _clsx.clsx)(prefixCls, {
    [`${prefixCls}-status`]: hasStatus,
    [`${prefixCls}-not-a-wrapper`]: !children,
    [`${prefixCls}-rtl`]: direction === 'rtl'
  }, className, rootClassName, contextClassName, mergedClassNames.root, hashId, cssVarCls);
  // <Badge status="success" />
  if (isStatusBadge) {
    const statusTextColor = mergedStyles.root?.color;
    return /*#__PURE__*/React.createElement("span", {
      ref: ref,
      ...restProps,
      className: badgeClassName,
      style: {
        ...offsetStyle,
        ...mergedStyles.root
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: statusCls,
      style: {
        ...mergedStyles.indicator,
        ...statusStyle
      }
    }), showStatusTextNode && (/*#__PURE__*/React.createElement("span", {
      style: {
        color: statusTextColor
      },
      className: `${prefixCls}-status-text`
    }, text)));
  }
  return /*#__PURE__*/React.createElement("span", {
    ref: ref,
    ...restProps,
    className: badgeClassName,
    style: mergedStyles.root
  }, children, /*#__PURE__*/React.createElement(_motion.default, {
    visible: !isHidden,
    motionName: `${prefixCls}-zoom`,
    motionAppear: false,
    motionDeadline: 1000
  }, ({
    className: motionClassName
  }) => {
    const scrollNumberPrefixCls = getPrefixCls('scroll-number', customizeScrollNumberPrefixCls);
    const isDot = isDotRef.current;
    const scrollNumberCls = (0, _clsx.clsx)(mergedClassNames.indicator, {
      [`${prefixCls}-dot`]: isDot,
      [`${prefixCls}-count`]: !isDot,
      [`${prefixCls}-count-sm`]: size === 'small',
      [`${prefixCls}-multiple-words`]: !isDot && displayCount && displayCount.toString().length > 1,
      [`${prefixCls}-status-${status}`]: !!status,
      [`${prefixCls}-color-${color}`]: isInternalColor
    });
    let scrollNumberStyle = {
      ...offsetStyle,
      ...mergedStyles.indicator
    };
    if (color && !isInternalColor) {
      scrollNumberStyle = scrollNumberStyle || {};
      scrollNumberStyle.background = color;
    }
    return /*#__PURE__*/React.createElement(_ScrollNumber.default, {
      prefixCls: scrollNumberPrefixCls,
      show: !isHidden,
      motionClassName: motionClassName,
      className: scrollNumberCls,
      count: displayCount,
      title: titleNode,
      style: scrollNumberStyle,
      key: "scrollNumber"
    }, displayNode);
  }), statusTextNode);
});
if (process.env.NODE_ENV !== 'production') {
  Badge.displayName = 'Badge';
}
var _default = exports.default = Badge;