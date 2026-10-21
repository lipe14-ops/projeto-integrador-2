import { unit } from '@ant-design/cssinjs';
import { resetComponent } from '../../style';
import { genStyleHooks } from '../../theme/internal';
const genListyStyle = token => {
  const {
    componentCls,
    itemPaddingBlock,
    itemPaddingInline
  } = token;
  return {
    [componentCls]: {
      ...resetComponent(token),
      position: 'relative',
      color: token.colorText,
      fontSize: token.fontSize,
      lineHeight: token.lineHeight,
      // ======================== Item ========================
      [`${componentCls}-item`]: {
        padding: `${unit(itemPaddingBlock)} ${unit(itemPaddingInline)}`,
        borderBottom: `${unit(token.lineWidth)} ${token.lineType} ${token.colorSplit}`,
        transition: `background-color ${token.motionDurationMid} ${token.motionEaseInOut}`,
        '&:hover': {
          backgroundColor: token.controlItemBgHover
        }
      },
      // ==================== Group header ====================
      [`${componentCls}-group-header`]: {
        boxSizing: 'border-box',
        padding: `${unit(token.paddingXS)} ${unit(itemPaddingInline)}`,
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
export const prepareComponentToken = token => ({
  itemPaddingBlock: token.paddingSM,
  itemPaddingInline: token.padding
});
export default genStyleHooks('Listy', genListyStyle, prepareComponentToken);