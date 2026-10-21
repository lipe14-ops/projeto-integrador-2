"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _bg_BG = _interopRequireDefault(require("@rc-component/picker/locale/bg_BG"));
var _bg_BG2 = _interopRequireDefault(require("../../time-picker/locale/bg_BG"));
// Merge into a locale object
const locale = {
  lang: {
    placeholder: 'Избор на дата',
    yearPlaceholder: 'Избор на година',
    quarterPlaceholder: 'Избор на тримесечие',
    monthPlaceholder: 'Избор на месец',
    weekPlaceholder: 'Избор на седмица',
    rangePlaceholder: ['Начална', 'Крайна'],
    rangeYearPlaceholder: ['Начална година', 'Крайна година'],
    rangeQuarterPlaceholder: ['Начално тримесечие', 'Крайно тримесечие'],
    rangeMonthPlaceholder: ['Начален месец', 'Краен месец'],
    rangeWeekPlaceholder: ['Начална седмица', 'Крайна седмица'],
    ..._bg_BG.default
  },
  timePickerLocale: {
    ..._bg_BG2.default
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/blob/master/components/date-picker/locale/example.json
var _default = exports.default = locale;