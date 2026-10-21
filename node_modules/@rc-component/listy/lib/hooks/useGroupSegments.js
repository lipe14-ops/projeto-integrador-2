"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useGroupSegments;
var React = _interopRequireWildcard(require("react"));
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
// ============================== Types ===============================

/**
 * Build a lookup map from group key to all matching data items and their
 * original indexes.
 * This groups by key across the full data set and does not require items with
 * the same key to be contiguous.
 */
function useGroupSegments(data, group) {
  return React.useMemo(() => {
    // ============================== Init ================================
    const map = new Map();

    // ============================ No Group ==============================
    if (!group) {
      return map;
    }

    // ============================= Collect ==============================
    data.forEach((item, index) => {
      const groupKey = group.key(item);
      const groupItems = map.get(groupKey);
      const groupSegmentItem = {
        item,
        index
      };
      if (groupItems) {
        groupItems.push(groupSegmentItem);
      } else {
        map.set(groupKey, [groupSegmentItem]);
      }
    });

    // ============================== Return ==============================
    return map;
  }, [data, group]);
}