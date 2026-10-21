"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.prepareComponentToken = exports.default = void 0;
var _cssinjs = require("@ant-design/cssinjs");
var _style = require("../../style");
var _internal = require("../../theme/internal");
const genListyStyle = token => {
  const {
    componentCls,
    itemPaddingBlock,
    itemPaddingInline
  } = token;
  return {
    [componentCls]: {
      ...(0, _style.resetComponent)(token),
      position: 'relative',
      color: token.colorText,
      fontSize: token.fontSize,
      lineHeight: token.lineHeight,
      // ======================== Item ========================
      [`${componentCls}-item`]: {
        padding: `${(0, _cssinjs.unit)(itemPaddingBlock)} ${(0, _cssinjs.unit)(itemPaddingInline)}`,
        borderBottom: `${(0, _cssinjs.unit)(token.lineWidth)} ${token.lineType} ${token.colorSplit}`,
        transition: `background-color ${token.motionDurationMid} ${token.motionEaseInOut}`,
        '&:hover': {
          backgroundColor: token.controlItemBgHover
        }
      },
      // ==================== Group header ====================
      [`${componentCls}-group-header`]: {
        boxSizing: 'border-box',
        padding: `${(0, _cssinjs.unit)(token.paddingXS)} ${(0, _cssinjs.unit)(itemPaddingInline)}`,
        color: token.colorTextDescription,
        fontWeight: token.fontWeightStrong,
        backgroundColor: token.colorBgContainer,
        backgroundImage: `linear-gradient(${token.colorFillAlter}, ${token.colorFillAlter})`,
        '&-sticky': {
          position: 'sticky',
          top: 0,
          insetInline: 0,
          zIndex: 1
        },
        '&-fixed': {
          position: 'absolute',
          top: 0,
          insetInline: 0,
          transform: 'translateY(0)',
          pointerEvents: 'auto'
        },
        '&-holder': {
          position: 'absolute',
          inset: 0,
          overflow: 'hidden',
          pointerEvents: 'none'
        }
      },
      [`${componentCls}-group-section`]: {
        position: 'relative'
      },
      [`${componentCls}-scrollbar`]: {
        zIndex: 1,
        cursor: 'pointer',
        '&:hover': {
          backgroundColor: token.colorFillQuaternary
        }
      },
      // ========================= RTL ========================
      '&-rtl': {
        direction: 'rtl'
      }
    }
  };
};
const prepareComponentToken = token => ({
  itemPaddingBlock: token.paddingSM,
  itemPaddingInline: token.padding
});
exports.prepareComponentToken = prepareComponentToken;
var _default = exports.default = (0, _internal.genStyleHooks)('Listy', genListyStyle, prepareComponentToken);