"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _pt_PT = _interopRequireDefault(require("@rc-component/picker/locale/pt_PT"));
var _pt_PT2 = _interopRequireDefault(require("../../time-picker/locale/pt_PT"));
// Merge into a locale object
const locale = {
  lang: {
    ..._pt_PT.default,
    placeholder: 'Data',
    yearPlaceholder: 'Ano',
    quarterPlaceholder: 'Trimestre',
    monthPlaceholder: 'Mês',
    weekPlaceholder: 'Semana',
    rangePlaceholder: ['Data inicial', 'Data final'],
    rangeYearPlaceholder: ['Ano inicial', 'Ano final'],
    rangeQuarterPlaceholder: ['Trimestre inicial', 'Trimestre final'],
    rangeMonthPlaceholder: ['Mês inicial', 'Mês final'],
    rangeWeekPlaceholder: ['Semana inicial', 'Semana final'],
    today: 'Hoje',
    now: 'Agora',
    backToToday: 'Hoje',
    ok: 'OK',
    clear: 'Limpar',
    month: 'Mês',
    year: 'Ano',
    timeSelect: 'Hora',
    dateSelect: 'Selecionar data',
    monthSelect: 'Selecionar mês',
    yearSelect: 'Selecionar ano',
    decadeSelect: 'Selecionar década',
    yearFormat: 'YYYY',
    monthFormat: 'MMMM',
    monthBeforeYear: false,
    previousMonth: 'Mês anterior (PageUp)',
    nextMonth: 'Mês seguinte (PageDown)',
    previousYear: 'Ano anterior (Control + left)',
    nextYear: 'Ano seguinte (Control + right)',
    previousDecade: 'Última década',
    nextDecade: 'Próxima década',
    previousCentury: 'Último século',
    nextCentury: 'Próximo século'
  },
  timePickerLocale: {
    ..._pt_PT2.default,
    placeholder: 'Hora'
  }
};
// All settings at:
// https://github.com/ant-design/ant-design/blob/master/components/date-picker/locale/example.json
var _default = exports.default = locale;