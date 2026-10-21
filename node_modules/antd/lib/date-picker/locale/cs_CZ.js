"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _cs_CZ = _interopRequireDefault(require("@rc-component/picker/locale/cs_CZ"));
var _cs_CZ2 = _interopRequireDefault(require("../../time-picker/locale/cs_CZ"));
// Merge into a locale object
const locale = {
  lang: {
    placeholder: 'Vybrat datum',
    yearPlaceholder: 'Vybrat rok',
    quarterPlaceholder: 'Vybrat čtvrtletí',
    monthPlaceholder: 'Vybrat měsíc',
    weekPlaceholder: 'Vybrat týden',
    rangePlaceholder: ['Od', 'Do'],
    rangeYearPlaceholder: ['Počáteční rok', 'Koncový rok'],
    rangeQuarterPlaceholder: ['Počáteční čtvrtletí', 'Koncové čtvrtletí'],
    rangeMonthPlaceholder: ['Počáteční měsíc', 'Koncový měsíc'],
    rangeWeekPlaceholder: ['Počáteční týden', 'Koncový týden'],
    ..._cs_CZ.default
  },
  timePickerLocale: {
    ..._cs_CZ2.default
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/blob/master/components/date-picker/locale/example.json
var _default = exports.default = locale;