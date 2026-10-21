"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _gl_ES = _interopRequireDefault(require("@rc-component/picker/locale/gl_ES"));
var _gl_ES2 = _interopRequireDefault(require("../../time-picker/locale/gl_ES"));
// Merge into a locale object
const locale = {
  lang: {
    placeholder: 'Escolla data',
    yearPlaceholder: 'Escolla ano',
    quarterPlaceholder: 'Escolla trimestre',
    monthPlaceholder: 'Escolla mes',
    weekPlaceholder: 'Escolla semana',
    rangePlaceholder: ['Data inicial', 'Data final'],
    rangeYearPlaceholder: ['Ano inicial', 'Ano final'],
    rangeQuarterPlaceholder: ['Trimestre inicial', 'Trimestre final'],
    rangeMonthPlaceholder: ['Mes inicial', 'Mes final'],
    rangeWeekPlaceholder: ['Semana inicial', 'Semana final'],
    ..._gl_ES.default
  },
  timePickerLocale: {
    ..._gl_ES2.default
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/blob/master/components/date-picker/locale/example.json
var _default = exports.default = locale;