"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useRawListScroll;
var React = _interopRequireWildcard(require("react"));
var _util = require("../util");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function useRawListScroll(ref, prefixCls, stickyGroup) {
  // =============================== Refs ===============================
  const holderRef = React.useRef(null);

  // ============================== Utils ===============================
  const getStickyHeaderHeight = React.useCallback(targetElement => {
    if (!stickyGroup) {
      return 0;
    }
    const groupSection = targetElement.closest(`.${CSS.escape(`${prefixCls}-group-section`)}`);
    const groupHeader = groupSection?.querySelector(`.${CSS.escape(`${prefixCls}-group-header`)}`);
    if (!groupHeader) {
      return 0;
    }
    const rect = groupHeader.getBoundingClientRect();
    const height = rect.height || rect.bottom - rect.top || groupHeader.offsetHeight;
    return Number.isFinite(height) ? height : 0;
  }, [prefixCls, stickyGroup]);
  const scrollTargetIntoView = React.useCallback((targetElement, align, offset, isItem) => {
    const headerOffset = isItem && align !== 'bottom' ? getStickyHeaderHeight(targetElement) : 0;
    const prevTop = targetElement.style.scrollMarginTop;
    const prevBottom = targetElement.style.scrollMarginBottom;
    targetElement.style.scrollMarginTop = `${headerOffset + offset}px`;
    targetElement.style.scrollMarginBottom = `${offset}px`;
    targetElement.scrollIntoView({
      block: align === 'bottom' ? 'end' : align === 'auto' ? 'nearest' : 'start',
      inline: 'nearest'
    });
    targetElement.style.scrollMarginTop = prevTop;
    targetElement.style.scrollMarginBottom = prevBottom;
  }, [getStickyHeaderHeight]);

  // ============================== Scroll ==============================
  const scrollTo = React.useCallback(config => {
    const holder = holderRef.current;
    if (!holder || config == null) {
      return;
    }
    if (typeof config === 'number') {
      holder.scrollTop = config;
      return;
    }
    if ('key' in config || 'groupKey' in config) {
      const {
        align = 'auto',
        offset = 0
      } = config;
      const isItem = ('key' in config);
      const targetKey = isItem ? (0, _util.toTaggedKey)(config.key, 'item') : (0, _util.toTaggedKey)(config.groupKey, 'group');
      const targetElement = holder.querySelector(`[data-key="${CSS.escape(targetKey)}"]`);
      if (targetElement) {
        scrollTargetIntoView(targetElement, align, offset, isItem);
      }
      return;
    }
    const {
      left,
      top
    } = config;
    if (left !== undefined) {
      holder.scrollLeft = left;
    }
    if (top !== undefined) {
      holder.scrollTop = top;
    }
  }, [scrollTargetIntoView]);

  // ============================ Imperative ============================
  React.useImperativeHandle(ref, () => ({
    scrollTo
  }), [scrollTo]);

  // ============================== Return ==============================
  return holderRef;
}