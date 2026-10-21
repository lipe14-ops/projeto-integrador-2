"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useFlattenRows;
var React = _interopRequireWildcard(require("react"));
var _util = require("../util");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
// ============================== Types ===============================

/**
 * Flatten grouped data into header and item rows.
 * When grouping is enabled, items follow the insertion order of the group map
 * while preserving their original indexes.
 */
function useFlattenRows(data, groupData, getItemKey, group) {
  return React.useMemo(() => {
    // ============================== Init ================================
    const flatRows = [];
    const groupKeys = [];
    const groupKeyToItems = new Map();
    const itemRow = (item, index) => ({
      type: 'item',
      item,
      index,
      taggedKey: (0, _util.toTaggedKey)(getItemKey(item), 'item')
    });

    // ============================ No Group ==============================
    if (!group) {
      data.forEach((item, index) => {
        flatRows.push(itemRow(item, index));
      });
      return {
        rows: flatRows,
        groupKeys,
        groupKeyToItems
      };
    }

    // ============================= Flatten ==============================
    groupData.forEach((groupItems, groupKey) => {
      groupKeyToItems.set(groupKey, groupItems.map(({
        item
      }) => item));
      groupKeys.push(groupKey);
      flatRows.push({
        type: 'group',
        groupKey,
        taggedKey: (0, _util.toTaggedKey)(groupKey, 'group')
      });
      groupItems.forEach(({
        item,
        index
      }) => {
        flatRows.push(itemRow(item, index));
      });
    });

    // ============================== Return ==============================
    return {
      rows: flatRows,
      groupKeys,
      groupKeyToItems
    };
  }, [data, group, groupData, getItemKey]);
}