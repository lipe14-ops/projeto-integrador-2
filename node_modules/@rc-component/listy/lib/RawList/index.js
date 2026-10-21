"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _clsx = _interopRequireDefault(require("clsx"));
var _GroupHeader = _interopRequireDefault(require("../GroupHeader"));
var _useGroupSegments = _interopRequireDefault(require("../hooks/useGroupSegments"));
var _useItemKey = _interopRequireDefault(require("../hooks/useItemKey"));
var _useRawListScroll = _interopRequireDefault(require("./useRawListScroll"));
var _util = require("../util");
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
// ============================== Types ===============================

function RawList(props, ref) {
  // ============================== Props ==============================
  const {
    data,
    group,
    height,
    itemRender,
    onScroll,
    prefixCls,
    rowKey,
    sticky,
    direction,
    classNames,
    styles
  } = props;

  // =============================== Refs ===============================
  const holderRef = (0, _useRawListScroll.default)(ref, prefixCls, !!(sticky && group));

  // =============================== Data ===============================
  const groupData = (0, _useGroupSegments.default)(data, group);

  // ============================== Utils ===============================
  const getItemKey = (0, _useItemKey.default)(rowKey);
  const getScrollTargetProps = React.useCallback((key, type) => ({
    'data-key': (0, _util.toTaggedKey)(key, type)
  }), []);

  // ============================ Render Item ===========================
  const renderItem = React.useCallback((item, index) => {
    const key = getItemKey(item);
    const scrollTargetProps = getScrollTargetProps(key, 'item');
    return /*#__PURE__*/React.createElement("div", _extends({
      key: key,
      className: (0, _clsx.default)(`${prefixCls}-item`, classNames?.item),
      style: styles?.item
    }, scrollTargetProps), itemRender(item, index));
  }, [classNames?.item, getItemKey, getScrollTargetProps, itemRender, prefixCls, styles?.item]);

  // ============================= Content ==============================
  const rawContent = group ? Array.from(groupData, ([groupKey, groupItems]) => {
    const currentGroupItems = groupItems.map(({
      item
    }) => item);
    return /*#__PURE__*/React.createElement("div", _extends({
      key: groupKey,
      className: `${prefixCls}-group-section`
    }, getScrollTargetProps(groupKey, 'group')), /*#__PURE__*/React.createElement(_GroupHeader.default, {
      group: group,
      groupKey: groupKey,
      groupItems: currentGroupItems,
      prefixCls: prefixCls,
      sticky: sticky,
      className: classNames?.groupHeader,
      style: styles?.groupHeader
    }), groupItems.map(({
      item,
      index
    }) => {
      return renderItem(item, index);
    }));
  }) : data.map((item, index) => {
    return renderItem(item, index);
  });

  // ============================== Render ==============================
  return /*#__PURE__*/React.createElement("div", {
    ref: holderRef,
    className: (0, _clsx.default)(prefixCls, {
      [`${prefixCls}-rtl`]: direction === 'rtl'
    }, classNames?.root),
    dir: direction,
    style: {
      maxHeight: height,
      overflowY: height === undefined ? undefined : 'auto',
      overflowAnchor: 'none',
      ...styles?.root
    },
    onScroll: onScroll
  }, rawContent);
}
const RawListWithRef = /*#__PURE__*/React.forwardRef(RawList);
var _default = exports.default = RawListWithRef;