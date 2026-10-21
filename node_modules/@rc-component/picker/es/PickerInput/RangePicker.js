function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
import { omit, pickAttrs, useControlledState, useEvent, useLayoutEffect, warning } from '@rc-component/util';
import { clsx } from 'clsx';
import * as React from 'react';
import PickerTrigger from "../PickerTrigger";
import { pickTriggerProps } from "../PickerTrigger/util";
import { isSameTimestamp } from "../utils/dateUtil";
import { fillIndex, getFromDate, toArray } from "../utils/miscUtil";
import PickerContext from "./context";
import useCellRender from "./hooks/useCellRender";
import useFieldsInvalidate from "./hooks/useFieldsInvalidate";
import useFilledProps from "./hooks/useFilledProps";
import useFocusEvents, { isTargetInContainers } from "./hooks/useFocusEvents";
import useFocusLock from "./hooks/useFocusLock";
import useOpen from "./hooks/useOpen";
import usePickerRef from "./hooks/usePickerRef";
import usePresets from "./hooks/usePresets";
import useRangeDisabledDate from "./hooks/useRangeDisabledDate";
import useRangePickerValue from "./hooks/useRangePickerValue";
import useRangeValue, { useInnerValue } from "./hooks/useRangeValue";
import useRangeValueChange from "./hooks/useRangeValueChange";
import useShowNow from "./hooks/useShowNow";
import Popup from "./Popup";
import RangeSelector from "./Selector/RangeSelector";
import useSemantic from "../hooks/useSemantic";
function separateConfig(config, defaultConfig) {
  const singleConfig = config ?? defaultConfig;
  if (Array.isArray(singleConfig)) {
    return singleConfig;
  }
  return [singleConfig, singleConfig];
}

/** Used for change event, it should always be not undefined */

function getActiveRange(activeIndex) {
  return activeIndex === 1 ? 'end' : 'start';
}
function RangePicker(props, ref) {
  // ========================= Prop =========================
  const [filledProps, internalPicker, complexPicker, formatList, maskFormat, isInvalidateDate] = useFilledProps(props, () => {
    const {
      disabled,
      allowEmpty
    } = props;
    const mergedDisabled = separateConfig(disabled, false);
    const mergedAllowEmpty = separateConfig(allowEmpty, false);
    return {
      disabled: mergedDisabled,
      allowEmpty: mergedAllowEmpty
    };
  });
  const {
    // Style
    prefixCls,
    rootClassName,
    styles: propStyles,
    classNames: propClassNames,
    previewValue,
    // Value
    defaultValue,
    value,
    needConfirm,
    onClear,
    onKeyDown,
    // Disabled
    disabled,
    allowEmpty,
    disabledDate,
    minDate,
    maxDate,
    // Open
    defaultOpen,
    open,
    onOpenChange,
    // Picker
    locale,
    generateConfig,
    picker,
    showNow,
    showToday,
    showTime,
    // Mode
    mode,
    onPanelChange,
    onCalendarChange,
    onOk,
    // Picker Value
    defaultPickerValue,
    pickerValue,
    onPickerValueChange,
    // Format
    inputReadOnly,
    suffixIcon,
    // Focus
    onFocus,
    onBlur,
    // Presets
    presets,
    ranges,
    // Render
    components,
    cellRender,
    dateRender,
    monthCellRender,
    // Native
    onClick
  } = filledProps;

  // ========================= Refs =========================
  const selectorRef = usePickerRef(ref);
  const popupRef = React.useRef(null);

  // ======================= Semantic =======================
  const [mergedClassNames, mergedStyles] = useSemantic(propClassNames, propStyles);

  // ========================= Open =========================
  const [mergedOpen, setMergeOpen] = useOpen(open, defaultOpen, disabled, onOpenChange);
  const triggerOpen = (nextOpen, config) => {
    // No need to open if all disabled
    if (disabled.some(fieldDisabled => !fieldDisabled) || !nextOpen) {
      setMergeOpen(nextOpen, config);
    }
  };

  // ======================== Values ========================
  const [mergedValue, setInnerValue, getCalendarValue, triggerCalendarChange, triggerOk] = useInnerValue(generateConfig, locale, formatList, true, false, defaultValue, value, onCalendarChange, onOk);
  const calendarValue = getCalendarValue();

  // ======================== Focus =========================
  const isInternalPickerElement = useEvent(element => isTargetInContainers(element, [selectorRef.current.nativeElement, popupRef.current]));
  const [focused, onFieldFocus, onFieldBlur] = useFocusEvents(isInternalPickerElement, (index, event) => {
    onFocus?.(event, {
      range: getActiveRange(index)
    });
  }, (index, event) => {
    onBlur?.(event, {
      range: getActiveRange(index)
    });
  }, () => {
    triggerOpen(false);
  });

  // ======================== Value =========================
  const [/** Trigger `onChange` by check `disabledDate` */
  flushSubmit, /** Trigger `onChange` directly without check `disabledDate` */
  triggerSubmitChange, /** Reset uncommitted values */
  resetValue] = useRangeValue(filledProps, mergedValue, setInnerValue, getCalendarValue, triggerCalendarChange, disabled, formatList, isInvalidateDate);
  const triggerFieldCalendarChange = useEvent((index, date) => {
    triggerCalendarChange(fillIndex(getCalendarValue(), index, date));
  });
  const flushFieldSubmit = useEvent((index, needTriggerChange) => {
    flushSubmit(index, needTriggerChange);
    if (needTriggerChange) {
      triggerOpen(false, {
        force: true
      });
    }
  });
  const enabledFieldCount = disabled.filter(fieldDisabled => !fieldDisabled).length;
  const [rangeValueIndex, activeIndex, forceFocus, triggeredFields, triggerRangeValueChange, resetRangeValueChange] = useRangeValueChange(enabledFieldCount, needConfirm, allowEmpty, getCalendarValue, triggerFieldCalendarChange, flushFieldSubmit, resetValue);
  useFocusLock(rangeValueIndex, forceFocus, selectorRef, popupRef, triggerOpen);

  // Finalize the current interaction only after the popup is actually closed.
  // 仅在 popup 实际关闭后，统一收口当前交互。
  useLayoutEffect(firstMount => {
    if (!firstMount && !mergedOpen) {
      triggerRangeValueChange(rangeValueIndex ?? activeIndex, 'popupClose');
    }
  }, [mergedOpen]);

  // ======================= ShowTime =======================
  /** Used for Popup panel */
  const mergedShowTime = React.useMemo(() => {
    if (!showTime) {
      return null;
    }
    const {
      disabledTime
    } = showTime;
    const proxyDisabledTime = disabledTime ? date => {
      const range = getActiveRange(activeIndex);
      const fromDate = getFromDate(calendarValue, triggeredFields, activeIndex);
      return disabledTime(date, range, {
        from: fromDate
      });
    } : undefined;
    return {
      ...showTime,
      disabledTime: proxyDisabledTime
    };
  }, [showTime, activeIndex, calendarValue, triggeredFields]);

  // ========================= Mode =========================
  const [modes, setModes] = useControlledState([picker, picker], mode);
  const mergedMode = modes[activeIndex] || picker;

  /** Extends from `mergedMode` to patch `datetime` mode */
  const internalMode = mergedMode === 'date' && mergedShowTime ? 'datetime' : mergedMode;

  // ====================== PanelCount ======================
  const multiplePanel = internalMode === picker && internalMode !== 'time';

  // ======================= Show Now =======================
  const mergedShowNow = useShowNow(picker, mergedMode, showNow, showToday, true);

  // ===================== DisabledDate =====================
  const mergedDisabledDate = useRangeDisabledDate(calendarValue, disabled, activeIndex, triggeredFields, generateConfig, locale, disabledDate);

  // ======================= Validate =======================
  const [submitInvalidates, onSelectorInvalid] = useFieldsInvalidate(calendarValue, isInvalidateDate, allowEmpty);

  // ===================== Picker Value =====================
  const [currentPickerValue, setCurrentPickerValue] = useRangePickerValue(generateConfig, locale, calendarValue, modes, mergedOpen, focused, activeIndex, internalPicker, multiplePanel, defaultPickerValue, pickerValue, mergedShowTime?.defaultOpenValue, onPickerValueChange, minDate, maxDate);

  // >>> Mode need wait for `pickerValue`
  const triggerModeChange = useEvent((nextPickerValue, nextMode, triggerEvent) => {
    const clone = fillIndex(modes, activeIndex, nextMode);
    if (clone[0] !== modes[0] || clone[1] !== modes[1]) {
      setModes(clone);
    }

    // Compatible with `onPanelChange`
    if (onPanelChange && triggerEvent !== false) {
      const clonePickerValue = [...calendarValue];
      if (nextPickerValue) {
        clonePickerValue[activeIndex] = nextPickerValue;
      }
      onPanelChange(clonePickerValue, clone);
    }
  });

  // ======================== Change ========================
  const fillCalendarValue = (date, index) =>
  // Trigger change only when date changed
  fillIndex(calendarValue, index, date);

  // ======================== Submit ========================
  /**
   * Trigger by confirm operation.
   * This function has already handle the `needConfirm` check logic.
   * - Selector: enter key
   * - Panel: OK button
   */
  const triggerPartConfirm = (date, source = 'confirm') => {
    triggerRangeValueChange(activeIndex, source, date ?? undefined);
  };

  // ======================== Click =========================
  const onSelectorClick = event => {
    const rootNode = event.target.getRootNode();
    if (!selectorRef.current.nativeElement.contains(rootNode.activeElement ?? document.activeElement)) {
      // Click to focus the enabled input
      const enabledIndex = disabled.findIndex(d => !d);
      if (enabledIndex >= 0) {
        selectorRef.current.focus({
          index: enabledIndex
        });
      }
    }
    triggerOpen(true);
    onClick?.(event);
  };
  const onSelectorClear = () => {
    resetRangeValueChange();
    triggerSubmitChange(null);
    triggerOpen(false, {
      force: true
    });
    onClear?.();
  };

  // ======================== Hover =========================
  const [hoverSource, setHoverSource] = React.useState(null);
  const [internalHoverValues, setInternalHoverValues] = React.useState(null);
  const hoverValues = React.useMemo(() => {
    return internalHoverValues || calendarValue;
  }, [calendarValue, internalHoverValues]);

  // "Weak" hover only highlights the hovered cell instead of composing a range.
  // Use it while choosing the first value so the pending selection remains selected.
  const showWeakHover =
  // Preset hover always previews the whole range.
  hoverSource === 'cell' &&
  // Once the other field has a value, range hover takes precedence.
  !calendarValue[(activeIndex + 1) % 2] &&
  // Only a changed active value needs weak hover.
  !isSameTimestamp(generateConfig, calendarValue[activeIndex], mergedValue[activeIndex]);
  const activeHoverValue = internalHoverValues?.[activeIndex];

  // Clean up `internalHoverValues` when closed
  React.useEffect(() => {
    if (!mergedOpen) {
      setInternalHoverValues(null);
    }
  }, [mergedOpen]);

  // ========================================================
  // ==                       Panels                       ==
  // ========================================================
  // Save the offset with active bar position
  // const [activeOffset, setActiveOffset] = React.useState(0);
  const [activeInfo, setActiveInfo] = React.useState([0, 0, 0]);
  const onSetHover = (date, source) => {
    if (previewValue !== 'hover') {
      return;
    }
    setInternalHoverValues(date);
    setHoverSource(source);
  };

  // ======================= Presets ========================
  const presetList = usePresets(presets, ranges);
  const onPresetHover = nextValues => {
    onSetHover(nextValues, 'preset');
  };
  const onPresetSubmit = nextValues => {
    const passed = triggerSubmitChange(nextValues);
    if (passed) {
      triggerOpen(false, {
        force: true
      });
    }
  };
  const onNow = now => {
    triggerPartConfirm(now);
  };

  // ======================== Panel =========================
  const onPanelHover = date => {
    onSetHover(date ? fillCalendarValue(date, activeIndex) : null, 'cell');
  };

  // >>> Focus
  const onPanelFocus = event => {
    triggerOpen(true);
    onFieldFocus(activeIndex, 'panel', event);
  };

  // >>> Calendar
  const onPanelSelect = date => {
    const panelFinished = !complexPicker && internalPicker === internalMode;
    triggerRangeValueChange(activeIndex, panelFinished ? 'panel-final' : 'panel-intermediate', date);
  };

  // >>> Close
  const onPopupClose = () => {
    triggerOpen(false);
  };

  // >>> cellRender
  const onInternalCellRender = useCellRender(cellRender, dateRender, monthCellRender, getActiveRange(activeIndex));

  // >>> Value
  const panelValue = calendarValue[activeIndex] || null;

  // >>> invalid
  const isPopupInvalidateDate = useEvent(date => {
    return isInvalidateDate(date, {
      activeIndex
    });
  });
  const panelProps = React.useMemo(() => {
    const domProps = pickAttrs(filledProps, false);
    const restProps = omit(filledProps, [...Object.keys(domProps), 'onChange', 'onCalendarChange', 'onClear', 'style', 'className', 'onPanelChange', 'disabledTime', 'classNames', 'styles']);
    return restProps;
  }, [filledProps]);

  // >>> Render
  const panel = /*#__PURE__*/React.createElement(Popup, _extends({
    containerRef: popupRef
    // MISC
  }, panelProps, {
    showNow: mergedShowNow,
    showTime: mergedShowTime
    // Range
    ,
    range: true,
    multiplePanel: multiplePanel,
    activeInfo: activeInfo
    // Disabled
    ,
    disabledDate: mergedDisabledDate
    // Focus
    ,
    onFocus: onPanelFocus,
    onBlur: event => onFieldBlur(activeIndex, 'panel', event)
    // Mode
    ,
    picker: picker,
    mode: mergedMode,
    internalMode: internalMode,
    onPanelChange: triggerModeChange
    // Value
    ,
    format: maskFormat,
    value: panelValue,
    isInvalid: isPopupInvalidateDate,
    onChange: null,
    onSelect: onPanelSelect
    // PickerValue
    ,
    pickerValue: currentPickerValue,
    defaultOpenValue: toArray(showTime?.defaultOpenValue)[activeIndex],
    onPickerValueChange: setCurrentPickerValue
    // Hover
    ,
    hoverValue: showWeakHover && activeHoverValue ? [activeHoverValue] : null,
    hoverRangeValue: showWeakHover ? null : hoverValues,
    onHover: onPanelHover
    // Submit
    ,
    needConfirm: needConfirm,
    onSubmit: date => triggerPartConfirm(date, 'confirm'),
    onOk: triggerOk
    // Preset
    ,
    presets: presetList,
    onPresetHover: onPresetHover,
    onPresetSubmit: onPresetSubmit
    // Now
    ,
    onNow: onNow
    // Render
    ,
    cellRender: onInternalCellRender
    // Styles
    ,
    classNames: mergedClassNames,
    styles: mergedStyles
  }));

  // ========================================================
  // ==                      Selector                      ==
  // ========================================================

  // ======================== Change ========================
  const onSelectorChange = (date, index) => {
    triggerRangeValueChange(index, 'input', date);
  };
  const onSelectorInputChange = () => {
    triggerRangeValueChange(activeIndex, 'input');
  };

  // ======================= Selector =======================
  const onSelectorFocus = (event, index) => {
    triggerRangeValueChange(index, 'field-switch');
    triggerOpen(true, {
      inherit: true
    });
    onFieldFocus(index, 'input', event);
  };
  const onSelectorBlur = (event, index) => {
    onFieldBlur(index, 'input', event);
  };
  const onSelectorKeyDown = (event, preventDefault) => {
    if (event.key === 'Tab') {
      triggerPartConfirm(null, 'keyboard-submit-weak');
    } else if (event.key === 'Escape') {
      triggerRangeValueChange(activeIndex, 'esc');
      triggerOpen(false);
    }
    onKeyDown?.(event, preventDefault);
  };

  // ======================= Context ========================
  const context = React.useMemo(() => ({
    prefixCls,
    locale,
    generateConfig,
    button: components.button,
    input: components.input,
    classNames: mergedClassNames,
    styles: mergedStyles
  }), [prefixCls, locale, generateConfig, components.button, components.input, mergedClassNames, mergedStyles]);

  // ======================== Effect ========================
  // >>> Mode
  // Reset for every active
  useLayoutEffect(() => {
    if (mergedOpen && activeIndex !== undefined) {
      // Legacy compatible. This effect update should not trigger `onPanelChange`
      triggerModeChange(null, picker, false);
    }
  }, [mergedOpen, activeIndex, picker]);

  // ====================== DevWarning ======================
  if (process.env.NODE_ENV !== 'production') {
    const isIndexEmpty = index => {
      return (
        // Value is empty
        !value?.[index] &&
        // DefaultValue is empty
        !defaultValue?.[index]
      );
    };
    if (disabled.some((fieldDisabled, index) => fieldDisabled && isIndexEmpty(index) && !allowEmpty[index])) {
      warning(false, '`disabled` should not set with empty `value`. You should set `allowEmpty` or `value` instead.');
    }
  }

  // ======================== Render ========================
  return /*#__PURE__*/React.createElement(PickerContext.Provider, {
    value: context
  }, /*#__PURE__*/React.createElement(PickerTrigger, _extends({}, pickTriggerProps(filledProps), {
    popupElement: panel,
    popupStyle: mergedStyles.popup.root,
    popupClassName: clsx(rootClassName, mergedClassNames.popup.root)
    // Visible
    ,
    visible: mergedOpen,
    onClose: onPopupClose
    // Range
    ,
    range: true
  }), /*#__PURE__*/React.createElement(RangeSelector
  // Shared
  , _extends({}, filledProps, {
    // Ref
    ref: selectorRef
    // Style
    ,
    className: clsx(filledProps.className, rootClassName, mergedClassNames.root),
    style: {
      ...mergedStyles.root,
      ...filledProps.style
    }
    // Icon
    ,
    suffixIcon: suffixIcon
    // Active
    ,
    activeIndex: focused || mergedOpen ? activeIndex : null,
    activeHelp: !!internalHoverValues,
    allHelp: !!internalHoverValues && hoverSource === 'preset',
    focused: focused,
    onFocus: onSelectorFocus,
    onBlur: onSelectorBlur,
    onKeyDown: onSelectorKeyDown,
    onSubmit: () => triggerPartConfirm(null, 'keyboard-submit')
    // Change
    ,
    value: hoverValues,
    maskFormat: maskFormat,
    onChange: onSelectorChange,
    onInputChange: onSelectorInputChange
    // Format
    ,
    format: formatList,
    inputReadOnly: inputReadOnly
    // Disabled
    ,
    disabled: disabled
    // Open
    ,
    open: mergedOpen,
    onOpenChange: triggerOpen
    // Click
    ,
    onClick: onSelectorClick,
    onClear: onSelectorClear
    // Invalid
    ,
    invalid: submitInvalidates,
    onInvalid: onSelectorInvalid
    // Offset
    ,
    onActiveInfo: setActiveInfo
  }))));
}
const RefRangePicker = /*#__PURE__*/React.forwardRef(RangePicker);
if (process.env.NODE_ENV !== 'production') {
  RefRangePicker.displayName = 'RefRangePicker';
}
export default RefRangePicker;