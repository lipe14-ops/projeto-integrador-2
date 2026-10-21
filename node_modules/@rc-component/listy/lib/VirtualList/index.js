"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _clsx = _interopRequireDefault(require("clsx"));
var _virtualList = _interopRequireDefault(require("@rc-component/virtual-list"));
var _util = require("@rc-component/util");
var _GroupHeader = _interopRequireDefault(require("../GroupHeader"));
var _util2 = require("../util");
var _useGroupSegments = _interopRequireDefault(require("../hooks/useGroupSegments"));
var _useItemKey = _interopRequireDefault(require("../hooks/useItemKey"));
var _useFlattenRows = _interopRequireDefault(require("./useFlattenRows"));
var _useStickyGroupHeader = _interopRequireDefault(require("./useStickyGroupHeader"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
// ============================== Types ===============================

function VirtualList(props, ref) {
  // ============================== Props ==============================
  const {
    data,
    group,
    height,
    itemHeight,
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
  const listRef = React.useRef(null);

  // =============================== Data ===============================
  const groupData = (0, _useGroupSegments.default)(data, group);

  // =============================== Keys ===============================
  const getItemKey = (0, _useItemKey.default)(rowKey);

  // ============================== Rows ================================
  const {
    rows,
    groupKeys,
    groupKeyToItems
  } = (0, _useFlattenRows.default)(data, groupData, getItemKey, group);

  // ============================== Lookup ==============================
  const itemKeyToGroupKey = React.useMemo(() => {
    const itemGroupMap = new Map();
    let currentGroupKey;
    rows.forEach(row => {
      if (row.type === 'group') {
        currentGroupKey = row.groupKey;
      } else if (currentGroupKey !== undefined) {
        itemGroupMap.set(row.taggedKey, currentGroupKey);
      }
    });
    return itemGroupMap;
  }, [rows]);

  // ============================== Scroll ==============================
  const scrollTo = (0, _util.useEvent)(config => {
    if (!config || typeof config !== 'object') {
      listRef.current?.scrollTo(config);
      return;
    }
    if ('groupKey' in config) {
      const {
        groupKey,
        align,
        offset
      } = config;
      listRef.current?.scrollTo({
        key: (0, _util2.toTaggedKey)(groupKey, 'group'),
        align,
        offset
      });
      return;
    }
    if ('key' in config) {
      const taggedItemKey = (0, _util2.toTaggedKey)(config.key, 'item');
      const stickyGroupKey = sticky && group && config.align !== 'bottom' ? itemKeyToGroupKey.get(taggedItemKey) : undefined;
      if (stickyGroupKey === undefined) {
        listRef.current?.scrollTo({
          ...config,
          key: taggedItemKey
        });
        return;
      }
      listRef.current?.scrollTo({
        ...config,
        key: taggedItemKey,
        offset: ({
          getSize,
          align
        }) => {
          const baseOffset = config.offset ?? 0;
          if (align !== 'top') {
            return baseOffset;
          }

          // Use the measured header height so the item stays below it.
          const headerSize = getSize((0, _util2.toTaggedKey)(stickyGroupKey, 'group'));
          const headerHeight = headerSize.bottom - headerSize.top;
          return baseOffset + (Number.isFinite(headerHeight) ? headerHeight : 0);
        }
      });
      return;
    }
    listRef.current?.scrollTo(config);
  });

  // ============================ Imperative ============================
  React.useImperativeHandle(ref, () => ({
    scrollTo
  }), [scrollTo]);

  // ============================== Sticky ==============================
  const extraRender = (0, _useStickyGroupHeader.default)({
    enabled: !!(sticky && group),
    group,
    groupKeys,
    groupKeyToItems,
    prefixCls,
    listRef,
    headerClassName: classNames?.groupHeader,
    headerStyle: styles?.groupHeader
  });

  // ============================ Render Row ============================
  const renderHeaderRow = React.useCallback(groupKey => {
    const groupItems = groupKeyToItems.get(groupKey) || [];
    return /*#__PURE__*/React.createElement(_GroupHeader.default, {
      group: group,
      groupKey: groupKey,
      groupItems: groupItems,
      prefixCls: prefixCls,
      className: classNames?.groupHeader,
      style: styles?.groupHeader
    });
  }, [classNames?.groupHeader, group, groupKeyToItems, prefixCls, styles?.groupHeader]);

  // ============================== Render ==============================
  return /*#__PURE__*/React.createElement(_virtualList.default, {
    ref: listRef,
    data: rows,
    direction: direction,
    fullHeight: false,
    height: height,
    itemHeight: itemHeight,
    itemKey: "taggedKey",
    onScroll: onScroll,
    prefixCls: prefixCls,
    virtual: true,
    extraRender: extraRender,
    className: classNames?.root,
    style: styles?.root
  }, row => row.type === 'group' ? renderHeaderRow(row.groupKey) : /*#__PURE__*/React.createElement("div", {
    className: (0, _clsx.default)(`${prefixCls}-item`, classNames?.item),
    style: styles?.item
  }, itemRender(row.item, row.index)));
}
const VirtualListWithRef = /*#__PURE__*/React.forwardRef(VirtualList);
var _default = exports.default = VirtualListWithRef;