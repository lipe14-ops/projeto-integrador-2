"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useRangePickerValue;
exports.offsetPanelDate = offsetPanelDate;
var _util = require("@rc-component/util");
var React = _interopRequireWildcard(require("react"));
var _dateUtil = require("../../utils/dateUtil");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function offsetPanelDate(generateConfig, picker, date, offset) {
  switch (picker) {
    case 'date':
    case 'week':
      return generateConfig.addMonth(date, offset);
    case 'month':
    case 'quarter':
      return generateConfig.addYear(date, offset);
    case 'year':
      return generateConfig.addYear(date, offset * 10);
    case 'decade':
      return generateConfig.addYear(date, offset * 100);
    default:
      return date;
  }
}
const EMPTY_LIST = [];
function useRangePickerValue(generateConfig, locale, calendarValue, modes, open, preserveOnFieldChange, activeIndex, pickerMode, multiplePanel, defaultPickerValue = EMPTY_LIST, pickerValue = EMPTY_LIST,
// This is legacy from origin logic.
// We will take `showTime.defaultValue` as the part of `pickerValue`
timeDefaultValue = EMPTY_LIST, onPickerValueChange, minDate, maxDate) {
  const isTimePicker = pickerMode === 'time';

  // ======================== Active ========================
  // `activeIndex` must be valid to avoid getting empty `pickerValue`
  const mergedActiveIndex = activeIndex || 0;
  const [startCalendarValue, endCalendarValue] = calendarValue;
  const activeCalendarValue = mergedActiveIndex === 0 ? startCalendarValue : endCalendarValue;
  const inactiveCalendarValue = mergedActiveIndex === 0 ? endCalendarValue : startCalendarValue;

  // ===================== Picker Value =====================
  const getDefaultPickerValue = index => {
    let now = generateConfig.getNow();
    if (isTimePicker) {
      now = (0, _dateUtil.fillTime)(generateConfig, now);
    }
    const calendarDate = index === 0 ? startCalendarValue : endCalendarValue;
    return defaultPickerValue[index] || calendarDate || now;
  };

  // Align `pickerValue` with `showTime.defaultValue`
  const [startPickerValue, endPickerValue] = pickerValue;

  // PickerValue state
  const [mergedStartPickerValue, setStartPickerValue] = (0, _util.useControlledState)(() => getDefaultPickerValue(0), startPickerValue);
  const [mergedEndPickerValue, setEndPickerValue] = (0, _util.useControlledState)(() => getDefaultPickerValue(1), endPickerValue);

  // Current PickerValue
  const currentPickerValue = React.useMemo(() => {
    const current = [mergedStartPickerValue, mergedEndPickerValue][mergedActiveIndex];

    // Merge the `showTime.defaultValue` into `pickerValue`
    return isTimePicker ? current : (0, _dateUtil.fillTime)(generateConfig, current, timeDefaultValue[mergedActiveIndex]);
  }, [isTimePicker, mergedStartPickerValue, mergedEndPickerValue, mergedActiveIndex, generateConfig, timeDefaultValue]);
  const setCurrentPickerValue = (nextPickerValue, source = 'panel') => {
    const updater = [setStartPickerValue, setEndPickerValue][mergedActiveIndex];
    updater(nextPickerValue);
    const clone = [mergedStartPickerValue, mergedEndPickerValue];
    clone[mergedActiveIndex] = nextPickerValue;
    if (onPickerValueChange && (!(0, _dateUtil.isSame)(generateConfig, locale, mergedStartPickerValue, clone[0], pickerMode) || !(0, _dateUtil.isSame)(generateConfig, locale, mergedEndPickerValue, clone[1], pickerMode))) {
      onPickerValueChange(clone, {
        source,
        range: mergedActiveIndex === 1 ? 'end' : 'start',
        mode: modes
      });
    }
  };

  // ======================== Effect ========================
  // Check whether two dates belong to the same panel.
  // 判断两个日期是否属于同一个面板。
  const isSamePanel = (date1, date2) => {
    if (pickerMode === 'year') {
      return Math.floor(generateConfig.getYear(date1) / 10) === Math.floor(generateConfig.getYear(date2) / 10);
    }
    const panelMode = pickerMode === 'month' || pickerMode === 'quarter' ? 'year' : 'month';
    return (0, _dateUtil.isSame)(generateConfig, locale, date1, date2, panelMode);
  };

  // Keep both values in the two visible panels when possible. Otherwise put
  // the end value in the second panel.
  // 尽量在双面板内同时展示两个值；无法容纳时，将 end 值放在右侧面板。
  const getEndDatePickerValue = (startDate, endDate) => {
    if (!multiplePanel || !startDate) {
      return endDate;
    }
    const nextPanelDate = offsetPanelDate(generateConfig, pickerMode, startDate, 1);
    const endInPanels = isSamePanel(startDate, endDate) || isSamePanel(nextPanelDate, endDate);
    return endInPanels ? startDate : offsetPanelDate(generateConfig, pickerMode, endDate, -1);
  };

  // >>> When switch field, reset the picker value as prev field picker value
  const prevActiveIndexRef = React.useRef(null);
  (0, _util.useLayoutEffect)(() => {
    if (open) {
      if (!defaultPickerValue[mergedActiveIndex]) {
        let nextPickerValue = isTimePicker ? null : generateConfig.getNow();

        /**
         * 1. If focus switches inside the open Picker, keep the current panels
         * 2. If current field has value, sync it to the panels
         *    - Start: use the start value
         *    - End: keep start when both values fit, otherwise put end on the second panel
         * 3. If current field has no value but another field has value, use another field value
         * 4. Else use now (not any `calendarValue` can ref)
         */

        if (preserveOnFieldChange && prevActiveIndexRef.current !== null && prevActiveIndexRef.current !== mergedActiveIndex) {
          // If from another field, not jump picker value
          nextPickerValue = [mergedStartPickerValue, mergedEndPickerValue][mergedActiveIndex ^ 1];
        } else if (activeCalendarValue) {
          // Current field has value
          nextPickerValue = mergedActiveIndex === 0 ? startCalendarValue : getEndDatePickerValue(startCalendarValue, endCalendarValue);
        } else if (inactiveCalendarValue) {
          // Current field has no value but another field has value
          nextPickerValue = inactiveCalendarValue;
        }

        // Only sync when has value, this will sync in the `min-max` logic
        if (nextPickerValue) {
          // nextPickerValue < minDate
          if (minDate && generateConfig.isAfter(minDate, nextPickerValue)) {
            nextPickerValue = minDate;
          }

          // maxDate < nextPickerValue
          const offsetPickerValue = multiplePanel ? offsetPanelDate(generateConfig, pickerMode, nextPickerValue, 1) : nextPickerValue;
          if (maxDate && generateConfig.isAfter(offsetPickerValue, maxDate)) {
            nextPickerValue = multiplePanel ? offsetPanelDate(generateConfig, pickerMode, maxDate, -1) : maxDate;
          }
          setCurrentPickerValue(nextPickerValue, 'reset');
        }
      }
    }
  }, [open, preserveOnFieldChange, mergedActiveIndex, calendarValue[mergedActiveIndex]]);

  // >>> Track previous field only during one continuous Picker focus session
  React.useEffect(() => {
    if (open && preserveOnFieldChange) {
      prevActiveIndexRef.current = mergedActiveIndex;
    } else {
      prevActiveIndexRef.current = null;
    }
  }, [open, preserveOnFieldChange, mergedActiveIndex]);

  // >>> defaultPickerValue: Resync to `defaultPickerValue` for each panel focused
  (0, _util.useLayoutEffect)(() => {
    if (open && defaultPickerValue) {
      if (defaultPickerValue[mergedActiveIndex]) {
        setCurrentPickerValue(defaultPickerValue[mergedActiveIndex], 'reset');
      }
    }
  }, [open, mergedActiveIndex]);
  return [currentPickerValue, setCurrentPickerValue];
}