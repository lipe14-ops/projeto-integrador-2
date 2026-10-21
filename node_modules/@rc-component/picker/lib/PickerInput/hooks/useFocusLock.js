"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useFocusLock;
var _util = require("@rc-component/util");
var React = _interopRequireWildcard(require("react"));
var _useFocusEvents = require("./useFocusEvents");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
/**
 * Keep focus on the specified input field while focus moves inside the Picker.
 * 当焦点在 Picker 内移动时，将其锁定在指定的输入框上。
 */
function useFocusLock(index, forceFocus, selectorRef, popupRef, triggerOpen) {
  const openPicker = (0, _util.useEvent)(() => {
    triggerOpen(true);
  });

  // Only a strong transition actively opens the Picker and moves DOM focus.
  // Weak transitions keep the expected index without stealing external focus.
  // 仅强切换会主动打开 Picker 并移动 DOM 焦点；弱切换只保留预期 index，
  // 不抢占外部元素的焦点。
  React.useEffect(() => {
    if (index !== null && forceFocus) {
      openPicker();
      selectorRef.current?.focus(index);
    }
  }, [index, forceFocus, openPicker]);

  // DOM focus may change while `index` stays the same, so check after every commit.
  // DOM 焦点变化时 `index` 可能保持不变，因此每次 commit 后都需要检查。
  (0, _util.useLayoutEffect)(() => {
    if (index === null) {
      return;
    }
    const inputFields = [selectorRef.current?.startInput, selectorRef.current?.endInput];
    const inputRoot = inputFields[index]?.getRootNode();

    // `document.activeElement` stops at the shadow host. Read from the input's
    // own root first so focus locking can identify the actual field.
    // `document.activeElement` 在 Shadow DOM 中只会返回 host。优先读取 input
    // 所属 root，才能识别实际聚焦的 field。
    const activeElement = inputRoot?.activeElement ?? document.activeElement;
    if ((0, _useFocusEvents.isTargetInContainers)(activeElement, [popupRef.current])) {
      return;
    }
    const focusInOtherField = inputFields.some((field, fieldIndex) => fieldIndex !== index && (0, _useFocusEvents.isTargetInContainers)(activeElement, [field]));
    if (focusInOtherField) {
      inputFields[index]?.focus();
    }
  });
}