import * as React from 'react';
import { forwardRef } from 'react';
import RawList from "./RawList";
import VirtualList from "./VirtualList";

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
  const listNode = virtual ? /*#__PURE__*/React.createElement(VirtualList, sharedListProps) : /*#__PURE__*/React.createElement(RawList, sharedListProps);
  return listNode;
}

// Const to support generic with forwardRef
const ListyWithForwardRef = /*#__PURE__*/forwardRef(Listy);
export default ListyWithForwardRef;