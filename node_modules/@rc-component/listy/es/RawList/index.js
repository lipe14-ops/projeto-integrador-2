function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
import * as React from 'react';
import clsx from 'clsx';
import GroupHeader from "../GroupHeader";
import useGroupSegments from "../hooks/useGroupSegments";
import useItemKey from "../hooks/useItemKey";
import useRawListScroll from "./useRawListScroll";
import { toTaggedKey } from "../util";

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
  const holderRef = useRawListScroll(ref, prefixCls, !!(sticky && group));

  // =============================== Data ===============================
  const groupData = useGroupSegments(data, group);

  // ============================== Utils ===============================
  const getItemKey = useItemKey(rowKey);
  const getScrollTargetProps = React.useCallback((key, type) => ({
    'data-key': toTaggedKey(key, type)
  }), []);

  // ============================ Render Item ===========================
  const renderItem = React.useCallback((item, index) => {
    const key = getItemKey(item);
    const scrollTargetProps = getScrollTargetProps(key, 'item');
    return /*#__PURE__*/React.createElement("div", _extends({
      key: key,
      className: clsx(`${prefixCls}-item`, classNames?.item),
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
    }, getScrollTargetProps(groupKey, 'group')), /*#__PURE__*/React.createElement(GroupHeader, {
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
    className: clsx(prefixCls, {
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
export default RawListWithRef;