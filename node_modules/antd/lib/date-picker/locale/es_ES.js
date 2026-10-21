"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _es_ES = _interopRequireDefault(require("@rc-component/picker/locale/es_ES"));
var _es_ES2 = _interopRequireDefault(require("../../time-picker/locale/es_ES"));
// Merge into a locale object
const locale = {
  lang: {
    placeholder: 'Seleccionar fecha',
    yearPlaceholder: 'Seleccionar año',
    quarterPlaceholder: 'Seleccionar trimestre',
    monthPlaceholder: 'Seleccionar mes',
    weekPlaceholder: 'Seleccionar semana',
    rangePlaceholder: ['Fecha inicial', 'Fecha final'],
    rangeYearPlaceholder: ['Año inicial', 'Año final'],
    rangeQuarterPlaceholder: ['Trimestre inicial', 'Trimestre final'],
    rangeMonthPlaceholder: ['Mes inicial', 'Mes final'],
    rangeWeekPlaceholder: ['Semana inicial', 'Semana final'],
    shortWeekDays: ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'],
    shortMonths: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
    ..._es_ES.default
  },
  timePickerLocale: {
    ..._es_ES2.default
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/blob/master/components/date-picker/locale/example.json
var _default = exports.default = locale;