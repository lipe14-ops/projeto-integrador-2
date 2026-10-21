"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _util = require("@rc-component/util");
var _clsx = require("clsx");
var React = _interopRequireWildcard(require("react"));
var _MotionThumb = _interopRequireDefault(require("./MotionThumb"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
function getValidTitle(option) {
  if (typeof option.title !== 'undefined') {
    return option.title;
  }

  // read `label` when title is `undefined`
  if (typeof option.label !== 'object') {
    return option.label?.toString();
  }
}
function normalizeOptions(options) {
  return options.map(option => {
    if (typeof option === 'object' && option !== null) {
      const validTitle = getValidTitle(option);
      return {
        ...option,
        value: option.value,
        title: validTitle
      };
    }
    return {
      label: option?.toString(),
      title: option?.toString(),
      value: option
    };
  });
}
const InternalSegmentedOption = ({
  prefixCls,
  className,
  style,
  styles,
  classNames: segmentedClassNames,
  data,
  disabled,
  checked,
  label,
  title,
  value,
  name,
  onChange,
  onFocus,
  onBlur,
  onKeyDown,
  onKeyUp,
  onMouseDown,
  itemRender = node => node
}) => {
  const handleChange = event => {
    if (disabled) {
      return;
    }
    onChange(event, value);
  };
  const itemContent = /*#__PURE__*/React.createElement("label", {
    className: (0, _clsx.clsx)(className, {
      [`${prefixCls}-item-disabled`]: disabled
    }),
    style: style,
    onMouseDown: onMouseDown
  }, /*#__PURE__*/React.createElement("input", {
    name: name,
    className: `${prefixCls}-item-input`,
    type: "radio",
    disabled: disabled,
    checked: checked,
    onChange: handleChange,
    onFocus: onFocus,
    onBlur: onBlur,
    onKeyDown: onKeyDown,
    onKeyUp: onKeyUp
  }), /*#__PURE__*/React.createElement("div", {
    className: (0, _clsx.clsx)(`${prefixCls}-item-label`, segmentedClassNames?.label),
    title: title,
    style: styles?.label
  }, label));
  return itemRender(itemContent, {
    item: data
  });
};
const Segmented = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    prefixCls = 'rc-segmented',
    direction,
    vertical,
    options = [],
    disabled,
    defaultValue,
    value,
    name,
    onChange,
    className = '',
    style,
    styles,
    classNames: segmentedClassNames,
    motionName = 'thumb-motion',
    itemRender,
    ...restProps
  } = props;
  const containerRef = React.useRef(null);
  const mergedRef = React.useMemo(() => (0, _util.composeRef)(containerRef, ref), [containerRef, ref]);
  const segmentedOptions = React.useMemo(() => {
    return normalizeOptions(options);
  }, [options]);

  // Note: We should not auto switch value when value not exist in options
  // which may break single source of truth.
  const [rawValue, setRawValue] = (0, _util.useControlledState)(defaultValue ?? segmentedOptions[0]?.value, value);

  // ======================= Change ========================
  const [thumbShow, setThumbShow] = React.useState(false);
  const handleChange = (event, val) => {
    setRawValue(val);
    onChange?.(val);
  };
  const divProps = (0, _util.omit)(restProps, ['children']);

  // ======================= Focus ========================
  const [isKeyboard, setIsKeyboard] = React.useState(false);
  const [isFocused, setIsFocused] = React.useState(false);
  const handleFocus = () => {
    setIsFocused(true);
  };
  const handleBlur = () => {
    setIsFocused(false);
  };
  const handleMouseDown = () => {
    setIsKeyboard(false);
  };

  // capture keyboard tab interaction for correct focus style
  const handleKeyUp = event => {
    if (event.key === 'Tab') {
      setIsKeyboard(true);
    }
  };

  // ======================= Keyboard ========================
  const onOffset = offset => {
    // keep the current option and not disabled options
    const validOptions = segmentedOptions.filter(option => option.value === rawValue || !option.disabled);
    const currentIndex = validOptions.findIndex(option => option.value === rawValue);
    const total = validOptions.length;
    const nextIndex = (currentIndex + offset + total) % total;
    const nextOption = validOptions[nextIndex];
    if (nextOption && nextOption.value !== rawValue) {
      setRawValue(nextOption.value);
      onChange?.(nextOption.value);
    }
  };
  const handleKeyDown = event => {
    switch (event.key) {
      case 'ArrowLeft':
      case 'ArrowUp':
        onOffset(-1);
        break;
      case 'ArrowRight':
      case 'ArrowDown':
        onOffset(1);
        break;
    }
  };
  const renderOption = segmentedOption => {
    const {
      value: optionValue,
      disabled: optionDisabled
    } = segmentedOption;
    return /*#__PURE__*/React.createElement(InternalSegmentedOption, _extends({}, segmentedOption, {
      name: name,
      data: segmentedOption,
      itemRender: itemRender,
      key: optionValue,
      prefixCls: prefixCls,
      className: (0, _clsx.clsx)(segmentedOption.className, `${prefixCls}-item`, segmentedClassNames?.item, {
        [`${prefixCls}-item-selected`]: optionValue === rawValue && !thumbShow,
        [`${prefixCls}-item-selected-text`]: optionValue === rawValue,
        [`${prefixCls}-item-focused`]: isFocused && isKeyboard && optionValue === rawValue
      }),
      style: styles?.item,
      classNames: segmentedClassNames,
      styles: styles,
      checked: optionValue === rawValue,
      onChange: handleChange,
      onFocus: handleFocus,
      onBlur: handleBlur,
      onKeyDown: handleKeyDown,
      onKeyUp: handleKeyUp,
      onMouseDown: handleMouseDown,
      disabled: !!disabled || !!optionDisabled
    }));
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    role: "radiogroup",
    "aria-label": "segmented control",
    tabIndex: disabled ? undefined : 0,
    "aria-orientation": vertical ? 'vertical' : 'horizontal',
    style: style
  }, divProps, {
    className: (0, _clsx.clsx)(prefixCls, {
      [`${prefixCls}-rtl`]: direction === 'rtl',
      [`${prefixCls}-disabled`]: disabled,
      [`${prefixCls}-vertical`]: vertical
    }, className),
    ref: mergedRef
  }), /*#__PURE__*/React.createElement("div", {
    className: `${prefixCls}-group`
  }, /*#__PURE__*/React.createElement(_MotionThumb.default, {
    vertical: vertical,
    prefixCls: prefixCls,
    value: rawValue,
    containerRef: containerRef,
    motionName: `${prefixCls}-${motionName}`,
    direction: direction,
    getValueIndex: val => segmentedOptions.findIndex(n => n.value === val),
    onMotionStart: () => {
      setThumbShow(true);
    },
    onMotionEnd: () => {
      setThumbShow(false);
    }
  }), segmentedOptions.map(renderOption)));
});
if (process.env.NODE_ENV !== 'production') {
  Segmented.displayName = 'Segmented';
}
const TypedSegmented = Segmented;
var _default = exports.default = TypedSegmented;