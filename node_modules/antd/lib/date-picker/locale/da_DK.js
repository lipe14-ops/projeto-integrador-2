"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _da_DK = _interopRequireDefault(require("@rc-component/picker/locale/da_DK"));
var _da_DK2 = _interopRequireDefault(require("../../time-picker/locale/da_DK"));
// Merge into a locale object
const locale = {
  lang: {
    placeholder: 'Vælg dato',
    yearPlaceholder: 'Vælg år',
    quarterPlaceholder: 'Vælg kvartal',
    monthPlaceholder: 'Vælg måned',
    weekPlaceholder: 'Vælg uge',
    rangePlaceholder: ['Startdato', 'Slutdato'],
    rangeYearPlaceholder: ['Startår', 'Slutår'],
    rangeQuarterPlaceholder: ['Startkvartal', 'Slutkvartal'],
    rangeMonthPlaceholder: ['Startmåned', 'Slutmåned'],
    rangeWeekPlaceholder: ['Startuge', 'Slutuge'],
    ..._da_DK.default
  },
  timePickerLocale: {
    ..._da_DK2.default
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/blob/master/components/date-picker/locale/example.json
var _default = exports.default = locale;