"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useStickyGroupHeader;
var React = _interopRequireWildcard(require("react"));
var _portal = _interopRequireDefault(require("@rc-component/portal"));
var _GroupHeader = _interopRequireDefault(require("../GroupHeader"));
var _util = require("../util");
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
// ============================== Types ===============================

// ============================== Utils ===============================
const HEADER_TOP_TOLERANCE = 1;
function findActiveHeaderIndex(groupKeys, getHeaderTop, scrollTop) {
  let left = 0;
  let right = groupKeys.length - 1;
  let activeIndex = 0;
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    if (getHeaderTop(groupKeys[mid]) <= scrollTop + HEADER_TOP_TOLERANCE) {
      activeIndex = mid;
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }
  return activeIndex;
}

// ============================== Params ==============================

function useStickyGroupHeader(params) {
  // ============================== Props ==============================
  const {
    enabled,
    group,
    groupKeys,
    groupKeyToItems,
    prefixCls,
    listRef,
    headerClassName,
    headerStyle
  } = params;

  // ============================ Extra Render ==========================
  const extraRender = React.useCallback(info => {
    const {
      getSize,
      scrollTop,
      virtual
    } = info;
    if (!enabled || !group || !groupKeys.length || !virtual) {
      return null;
    }
    const container = listRef.current?.nativeElement;
    if (!container) {
      return null;
    }
    const getGroupSize = groupKey => getSize((0, _util.toTaggedKey)(groupKey, 'group'));

    // The sticky header is the group whose section the viewport top sits in.
    const activeHeaderIdx = findActiveHeaderIndex(groupKeys, groupKey => getGroupSize(groupKey).top, scrollTop);
    const currGroupKey = groupKeys[activeHeaderIdx];
    const groupItems = groupKeyToItems.get(currGroupKey) || [];
    const currentSize = getGroupSize(currGroupKey);
    const headerHeight = currentSize.bottom - currentSize.top;
    const nextGroupKey = groupKeys[activeHeaderIdx + 1];
    // Explicit undefined check: a falsy group key (0, '') is still a group.
    const top = nextGroupKey !== undefined ? Math.min(0, getGroupSize(nextGroupKey).top - headerHeight - scrollTop) : 0;

    // Render a cloned header pinned over the virtual list.
    return /*#__PURE__*/React.createElement(_portal.default, {
      open: true,
      getContainer: () => container
    }, /*#__PURE__*/React.createElement("div", {
      className: `${prefixCls}-group-header-holder`
    }, /*#__PURE__*/React.createElement(_GroupHeader.default, {
      fixed: true,
      group: group,
      groupKey: currGroupKey,
      groupItems: groupItems,
      prefixCls: prefixCls,
      className: headerClassName
      // `top` is the computed sticky-push offset and must win over any
      // user-supplied top in headerStyle, or the sticky behavior breaks.
      ,
      style: {
        ...headerStyle,
        top
      }
    })));
  }, [enabled, group, groupKeys, groupKeyToItems, prefixCls, listRef, headerClassName, headerStyle]);

  // ============================== Return ==============================
  return extraRender;
}