"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _it_IT = _interopRequireDefault(require("@rc-component/picker/locale/it_IT"));
var _it_IT2 = _interopRequireDefault(require("../../time-picker/locale/it_IT"));
// Merge into a locale object
const locale = {
  lang: {
    placeholder: 'Selezionare la data',
    yearPlaceholder: "Selezionare l'anno",
    quarterPlaceholder: 'Selezionare il trimestre',
    monthPlaceholder: 'Selezionare il mese',
    weekPlaceholder: 'Selezionare la settimana',
    rangePlaceholder: ["Data d'inizio", 'Data di fine'],
    rangeYearPlaceholder: ["Anno d'inizio", 'Anno di fine'],
    rangeQuarterPlaceholder: ["Trimestre d'inizio", 'Trimestre di fine'],
    rangeMonthPlaceholder: ["Mese d'inizio", 'Mese di fine'],
    rangeWeekPlaceholder: ["Settimana d'inizio", 'Settimana di fine'],
    ..._it_IT.default
  },
  timePickerLocale: {
    ..._it_IT2.default
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/issues/424
var _default = exports.default = locale;