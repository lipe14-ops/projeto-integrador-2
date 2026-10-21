"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _RawList = _interopRequireDefault(require("./RawList"));
var _VirtualList = _interopRequireDefault(require("./VirtualList"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
// ============================== Types ===============================

function Listy(props, ref) {
  // ============================== Props ==============================
  const {
    items,
    virtual = true,
    prefixCls = 'rc-listy',
    ...restProps
  } = props;

  // =============================== Data ===============================
  const data = React.useMemo(() => items || [], [items]);

  // ============================== Render ===============================
  const sharedListProps = {
    ...restProps,
    data,
    prefixCls,
    ref
  };
  const listNode = virtual ? /*#__PURE__*/React.createElement(_VirtualList.default, sharedListProps) : /*#__PURE__*/React.createElement(_RawList.default, sharedListProps);
  return listNode;
}

// Const to support generic with forwardRef
const ListyWithForwardRef = /*#__PURE__*/(0, _react.forwardRef)(Listy);
var _default = exports.default = ListyWithForwardRef;