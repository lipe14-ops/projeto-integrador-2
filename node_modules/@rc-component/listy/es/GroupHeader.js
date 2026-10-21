import * as React from 'react';
import clsx from 'clsx';

// ============================== Types ===============================

function GroupHeader(props, ref) {
  // ============================== Props ==============================
  const {
    group,
    groupKey,
    groupItems,
    prefixCls,
    fixed,
    sticky,
    className: customClassName,
    style
  } = props;

  // ============================= Classes =============================
  const className = clsx(`${prefixCls}-group-header`, {
    [`${prefixCls}-group-header-sticky`]: sticky,
    [`${prefixCls}-group-header-fixed`]: fixed
  }, customClassName);

  // ============================== Render ==============================
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    className: className,
    style: style
  }, group.title(groupKey, groupItems));
}
const GroupHeaderWithRef = /*#__PURE__*/React.forwardRef(GroupHeader);
export default GroupHeaderWithRef;