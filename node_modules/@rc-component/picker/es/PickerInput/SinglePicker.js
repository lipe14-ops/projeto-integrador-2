function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
import { omit, pickAttrs, useControlledState, useEvent, useLayoutEffect } from '@rc-component/util';
import { clsx } from 'clsx';
import * as React from 'react';
import useToggleDates from "../hooks/useToggleDates";
import PickerTrigger from "../PickerTrigger";
import { pickTriggerProps } from "../PickerTrigger/util";
import { toArray } from "../utils/miscUtil";
import PickerContext from "./context";
import useCellRender from "./hooks/useCellRender";
import useFieldsInvalidate from "./hooks/useFieldsInvalidate";
import useFilledProps from "./hooks/useFilledProps";
import useFocusEvents, { isTargetInContainers } from "./hooks/useFocusEvents";
import useOpen from "./hooks/useOpen";
import usePickerRef from "./hooks/usePickerRef";
import usePresets from "./hooks/usePresets";
import useRangePickerValue from "./hooks/useRangePickerValue";
import useRangeValue, { useInnerValue } from "./hooks/useRangeValue";
import useRangeValueChange from "./hooks/useRangeValueChange";
import useShowNow from "./hooks/useShowNow";
import Popup from "./Popup";
import SingleSelector from "./Selector/SingleSelector";
import useSemantic from "../hooks/useSemantic";

// TODO: isInvalidateDate with showTime.disabledTime should not provide `range` prop

/** Internal usage. For cross function get same aligned props */

function Picker(props, ref) {
  // ========================= Prop =========================
  const [filledProps, internalPicker, complexPicker, formatList, maskFormat, isInvalidateDate] = useFilledProps(props);
  const {
    // Style
    prefixCls,
    rootClassName,
    styles: propStyles,
    classNames: propClassNames,
    previewValue,
    // Value
    order,
    defaultValue,
    value,
    needConfirm,
    onChange,
    onClear,
    onKeyDown,
    // Disabled
    disabled,
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
    multiple,
    // Picker Value
    defaultPickerValue,
    pickerValue,
    onPickerValueChange,
    // Format
    inputReadOnly,
    suffixIcon,
    removeIcon,
    tagRender,
    // Focus
    onFocus,
    onBlur,
    // Presets
    presets,
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

  // ========================= Util =========================
  function pickerParam(values) {
    if (values === null) {
      return null;
    }
    return multiple ? values : values[0];
  }
  const toggleDates = useToggleDates(generateConfig, locale, internalPicker);

  // ======================= Semantic =======================
  const [mergedClassNames, mergedStyles] = useSemantic(propClassNames, propStyles);

  // ========================= Open =========================
  const [mergedOpen, triggerOpen] = useOpen(open, defaultOpen, [disabled], onOpenChange);

  // ======================= Calendar =======================
  const onInternalCalendarChange = (dates, dateStrings, info) => {
    if (onCalendarChange) {
      const filteredInfo = {
        ...info
      };
      delete filteredInfo.range;
      onCalendarChange(pickerParam(dates), pickerParam(dateStrings), filteredInfo);
    }
  };
  const onInternalOk = dates => {
    onOk?.(pickerParam(dates));
  };

  // ======================== Values ========================
  const [mergedValue, setInnerValue, getCalendarValue, triggerCalendarChange, triggerOk] = useInnerValue(generateConfig, locale, formatList, false, order, defaultValue, value, onInternalCalendarChange, onInternalOk);
  const calendarValue = getCalendarValue();

  // ======================== Focus =========================
  const isInternalPickerElement = useEvent(element => isTargetInContainers(element, [selectorRef.current.nativeElement, popupRef.current]));
  const [focused, onFieldFocus, onFieldBlur] = useFocusEvents(isInternalPickerElement, (_index, event) => {
    onFocus?.(event, {});
  }, (_index, event) => {
    onBlur?.(event, {});
  }, () => {
    triggerOpen(false);
  });

  // ========================= Mode =========================
  const [mergedMode, setMode] = useControlledState(picker, mode);

  /** Extends from `mergedMode` to patch `datetime` mode */
  const internalMode = mergedMode === 'date' && showTime ? 'datetime' : mergedMode;

  // ======================= Show Now =======================
  const mergedShowNow = useShowNow(picker, mergedMode, showNow, showToday);

  // ======================== Value =========================
  const onInternalChange = onChange && ((dates, dateStrings) => {
    onChange(pickerParam(dates), pickerParam(dateStrings));
  });
  const [, /** Trigger `onChange` directly without check `disabledDate` */
  triggerSubmitChange, /** Reset uncommitted values */
  resetValue] = useRangeValue({
    ...filledProps,
    onChange: onInternalChange
  }, mergedValue, setInnerValue, getCalendarValue, triggerCalendarChange, [],
  //disabled,
  formatList, isInvalidateDate);

  // Treat the complete SinglePicker value list as one field value. This keeps
  // multiple dates inside field `0` instead of exposing them as extra fields.
  // 将 SinglePicker 的整组值视为一个 field value；multiple 日期仍属于
  // field `0` 内部，不会被当成额外的 field。
  const getFieldCalendarValue = useEvent(() => {
    const values = getCalendarValue();
    return [values.length ? values : null];
  });
  const triggerFieldCalendarChange = useEvent((_index, nextValues) => {
    triggerCalendarChange(nextValues);
  });
  const flushFieldSubmit = useEvent((_index, needTriggerChange) => {
    if (needTriggerChange) {
      triggerSubmitChange(getCalendarValue());
      triggerOpen(false, {
        force: true
      });
    }
  });
  const resetFieldValue = useEvent(() => {
    resetValue();
  });
  const [, activeIndex,,, triggerSingleValueChange, resetSingleValueChange] = useRangeValueChange(1, needConfirm, [false], getFieldCalendarValue, triggerFieldCalendarChange, flushFieldSubmit, resetFieldValue);

  // Finalize the current interaction only after the popup is actually closed.
  // 仅在 popup 实际关闭后，统一收口当前交互。
  useLayoutEffect(firstMount => {
    if (!firstMount && !mergedOpen) {
      triggerSingleValueChange(0, 'popupClose');
    }
  }, [mergedOpen]);

  // ======================= Validate =======================
  const [submitInvalidates, onSelectorInvalid] = useFieldsInvalidate(calendarValue, isInvalidateDate);
  const submitInvalidate = React.useMemo(() => submitInvalidates.some(invalidated => invalidated), [submitInvalidates]);

  // ===================== Picker Value =====================
  // Proxy to single pickerValue
  const onInternalPickerValueChange = (dates, info) => {
    if (onPickerValueChange) {
      const cleanInfo = {
        ...info,
        mode: info.mode[0]
      };
      delete cleanInfo.range;
      onPickerValueChange(dates[0], cleanInfo);
    }
  };
  const [currentPickerValue, setCurrentPickerValue] = useRangePickerValue(generateConfig, locale, calendarValue, [mergedMode], mergedOpen, false, activeIndex, internalPicker, false,
  // multiplePanel,
  defaultPickerValue, pickerValue, toArray(showTime?.defaultOpenValue), onInternalPickerValueChange, minDate, maxDate);

  // >>> Mode need wait for `pickerValue`
  const triggerModeChange = useEvent((nextPickerValue, nextMode, triggerEvent) => {
    setMode(nextMode);

    // Compatible with `onPanelChange`
    if (onPanelChange && triggerEvent !== false) {
      const lastPickerValue = nextPickerValue || calendarValue[calendarValue.length - 1];
      onPanelChange(lastPickerValue, nextMode);
    }
  });

  // ======================== Submit ========================
  /**
   * Submit the complete value list stored in SinglePicker field `0`.
   * 提交 SinglePicker field `0` 内保存的整组值。
   */
  const triggerConfirm = (source = 'confirm') => {
    triggerSingleValueChange(0, source);
  };

  // ======================== Click =========================
  const onSelectorClick = event => {
    if (!disabled && !selectorRef.current.nativeElement.contains(document.activeElement)) {
      // Click to focus the enabled input
      selectorRef.current.focus();
    }
    triggerOpen(true);
    onClick?.(event);
  };
  const onSelectorClear = () => {
    resetSingleValueChange();
    triggerSubmitChange(null);
    triggerOpen(false, {
      force: true
    });
    selectorRef.current.focus();
    onClear?.();
  };

  // ======================== Hover =========================
  const [hoverSource, setHoverSource] = React.useState(null);
  const [internalHoverValue, setInternalHoverValue] = React.useState(null);
  const hoverValues = React.useMemo(() => {
    const values = [internalHoverValue, ...calendarValue].filter(date => date);
    return multiple ? values : values.slice(0, 1);
  }, [calendarValue, internalHoverValue, multiple]);

  // Selector values is different with RangePicker
  // which can not use `hoverValue` directly
  const selectorValues = React.useMemo(() => {
    if (!multiple && internalHoverValue) {
      return [internalHoverValue];
    }
    return calendarValue.filter(date => date);
  }, [calendarValue, internalHoverValue, multiple]);

  // Clean up `internalHoverValues` when closed
  React.useEffect(() => {
    if (!mergedOpen) {
      setInternalHoverValue(null);
    }
  }, [mergedOpen]);
  const onSetHover = (date, source) => {
    if (previewValue !== 'hover') {
      return;
    }
    setInternalHoverValue(date);
    setHoverSource(source);
  };

  // ========================================================
  // ==                       Panels                       ==
  // ========================================================
  // ======================= Presets ========================
  const presetList = usePresets(presets);
  const onPresetHover = nextValue => {
    onSetHover(nextValue, 'preset');
  };

  // TODO: handle this
  const onPresetSubmit = nextValue => {
    const nextCalendarValues = multiple ? toggleDates(getCalendarValue(), nextValue) : [nextValue];
    const passed = triggerSubmitChange(nextCalendarValues);
    if (passed && !multiple) {
      triggerOpen(false, {
        force: true
      });
    }
  };
  const onNow = now => {
    onPresetSubmit(now);
  };

  // ======================== Panel =========================
  const onPanelHover = date => {
    onSetHover(date, 'cell');
  };

  // >>> Focus
  const onPanelFocus = event => {
    triggerOpen(true);
    onFieldFocus(0, 'panel', event);
  };

  // >>> Calendar
  const onPanelSelect = date => {
    // Not change values if multiple and current panel is to match with picker
    if (multiple && internalMode !== picker) {
      return;
    }
    const nextValues = multiple ? toggleDates(getCalendarValue(), date) : [date];
    const panelFinished = !complexPicker && internalPicker === internalMode;
    triggerSingleValueChange(0, panelFinished ? 'panel-final' : 'panel-intermediate', nextValues);
  };

  // >>> Close
  const onPopupClose = () => {
    // Close popup
    triggerOpen(false);
  };

  // >>> cellRender
  const onInternalCellRender = useCellRender(cellRender, dateRender, monthCellRender);

  // >>> invalid

  const panelProps = React.useMemo(() => {
    const domProps = pickAttrs(filledProps, false);
    const restProps = omit(filledProps, [...Object.keys(domProps), 'onChange', 'onCalendarChange', 'onClear', 'style', 'className', 'onPanelChange', 'classNames', 'styles']);
    return {
      ...restProps,
      multiple: filledProps.multiple
    };
  }, [filledProps]);

  // >>> Render
  const panel = /*#__PURE__*/React.createElement(Popup, _extends({
    containerRef: popupRef
    // MISC
  }, panelProps, {
    showNow: mergedShowNow,
    showTime: showTime
    // Disabled
    ,
    disabledDate: disabledDate
    // Focus
    ,
    onFocus: onPanelFocus,
    onBlur: event => onFieldBlur(0, 'panel', event)
    // Mode
    ,
    picker: picker,
    mode: mergedMode,
    internalMode: internalMode,
    onPanelChange: triggerModeChange
    // Value
    ,
    format: maskFormat,
    value: calendarValue,
    isInvalid: isInvalidateDate,
    onChange: null,
    onSelect: onPanelSelect
    // PickerValue
    ,
    pickerValue: currentPickerValue,
    defaultOpenValue: showTime?.defaultOpenValue,
    onPickerValueChange: setCurrentPickerValue
    // Hover
    ,
    hoverValue: hoverValues,
    onHover: onPanelHover
    // Submit
    ,
    needConfirm: needConfirm,
    onSubmit: () => triggerConfirm('confirm'),
    onOk: triggerOk
    // Preset
    ,
    presets: presetList,
    onPresetHover: onPresetHover,
    onPresetSubmit: onPresetSubmit,
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
  const onSelectorChange = (date, source = 'input') => {
    triggerSingleValueChange(0, source, date);
  };
  const onSelectorInputChange = () => {
    triggerSingleValueChange(0, 'input');
  };

  // ======================= Selector =======================
  const onSelectorFocus = event => {
    triggerSingleValueChange(0, 'field-switch');
    triggerOpen(true, {
      inherit: true
    });
    onFieldFocus(0, 'input', event);
  };
  const onSelectorBlur = event => {
    onFieldBlur(0, 'input', event);
  };
  const onSelectorKeyDown = (event, preventDefault) => {
    if (event.key === 'Tab') {
      triggerConfirm('keyboard-submit-weak');
    } else if (event.key === 'Escape') {
      triggerSingleValueChange(0, 'esc');
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
  }), /*#__PURE__*/React.createElement(SingleSelector
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
    suffixIcon: suffixIcon,
    removeIcon: removeIcon,
    tagRender: tagRender
    // Active
    ,
    activeHelp: !!internalHoverValue,
    allHelp: !!internalHoverValue && hoverSource === 'preset',
    focused: focused,
    onFocus: onSelectorFocus,
    onBlur: onSelectorBlur,
    onKeyDown: onSelectorKeyDown,
    onSubmit: () => triggerConfirm('keyboard-submit')
    // Change
    ,
    value: selectorValues,
    maskFormat: maskFormat,
    onChange: onSelectorChange,
    onInputChange: onSelectorInputChange,
    internalPicker: internalPicker
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
    invalid: submitInvalidate,
    onInvalid: invalid => {
      // Only `single` mode support type date.
      // `multiple` mode can not typing.
      onSelectorInvalid(invalid, 0);
    }
  }))));
}
const RefPicker = /*#__PURE__*/React.forwardRef(Picker);
if (process.env.NODE_ENV !== 'production') {
  RefPicker.displayName = 'RefPicker';
}
export default RefPicker;