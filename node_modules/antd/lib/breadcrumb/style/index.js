"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.prepareComponentToken = exports.default = void 0;
var _cssinjs = require("@ant-design/cssinjs");
var _style = require("../../style");
var _internal = require("../../theme/internal");
const genBreadcrumbStyle = token => {
  const {
    componentCls,
    iconCls,
    calc
  } = token;
  return {
    [componentCls]: {
      ...(0, _style.resetComponent)(token),
      color: token.itemColor,
      fontSize: token.fontSize,
      [iconCls]: {
        fontSize: token.iconFontSize
      },
      ol: {
        display: 'flex',
        flexWrap: 'wrap',
        margin: 0,
        padding: 0,
        listStyle: 'none'
      },
      [`${componentCls}-item a`]: {
        color: token.linkColor,
        transition: `color ${token.motionDurationMid}`,
        padding: `0 ${(0, _cssinjs.unit)(token.paddingXXS)}`,
        borderRadius: token.borderRadiusSM,
        height: token.fontHeight,
        display: 'inline-block',
        marginInline: calc(token.marginXXS).mul(-1).equal(),
        '&:hover': {
          color: token.linkHoverColor,
          backgroundColor: token.colorBgTextHover
        },
        ...(0, _style.genFocusStyle)(token)
      },
      [`${componentCls}-item:last-child`]: {
        color: token.lastItemColor
      },
      [`${componentCls}-separator`]: {
        marginInline: token.separatorMargin,
        color: token.separatorColor
      },
      [`${componentCls}-link`]: {
        // Icons from third-party libraries render as a bare `<svg>`, which the `.anticon`
        // reset never reaches. An `<svg>` has no baseline of its own, so it is aligned by its
        // bottom margin edge (CSS 2.1 §10.8.1) and rides above the link text.
        // `display: inline-block` keeps it an atomic inline box so `vertical-align` still applies
        // even under a CSS reset that forces `svg { display: block }` (e.g. Tailwind Preflight),
        // which would otherwise drop the icon onto its own line. `vertical-align: middle` centres
        // its margin box on the x-height line; `margin-block-end` then lifts it by half its own
        // value onto the cap-height centre (capHeight − xHeight ≈ 0.2em across typical fonts),
        // keeping it centred at any icon size.
        // Only matches a bare `<svg>`: an `.anticon` keeps its `<svg>` one level deeper.
        '> svg': {
          display: 'inline-block',
          verticalAlign: 'middle',
          marginBlockEnd: '0.2em'
        },
        // Same spacing an `.anticon` gets before the following text, extended to a bare `<svg>`.
        [`
          > ${iconCls} + span,
          > ${iconCls} + a,
          > svg + span,
          > svg + a
        `]: {
          marginInlineStart: token.marginXXS
        }
      },
      [`${componentCls}-overlay-link`]: {
        borderRadius: token.borderRadiusSM,
        height: token.fontHeight,
        display: 'inline-block',
        padding: `0 ${(0, _cssinjs.unit)(token.paddingXXS)}`,
        marginInline: calc(token.marginXXS).mul(-1).equal(),
        [`> ${iconCls}`]: {
          marginInlineStart: token.marginXXS,
          fontSize: token.fontSizeIcon
        },
        '&:hover': {
          color: token.linkHoverColor,
          backgroundColor: token.colorBgTextHover,
          a: {
            color: token.linkHoverColor
          }
        },
        a: {
          '&:hover': {
            backgroundColor: 'transparent'
          }
        }
      },
      // rtl style
      [`&${token.componentCls}-rtl`]: {
        direction: 'rtl'
      }
    }
  };
};
const prepareComponentToken = token => ({
  itemColor: token.colorTextDescription,
  lastItemColor: token.colorText,
  iconFontSize: token.fontSize,
  linkColor: token.colorTextDescription,
  linkHoverColor: token.colorText,
  separatorColor: token.colorTextDescription,
  separatorMargin: token.marginXS
});
// ============================== Export ==============================
exports.prepareComponentToken = prepareComponentToken;
var _default = exports.default = (0, _internal.genStyleHooks)('Breadcrumb', token => {
  const breadcrumbToken = (0, _internal.mergeToken)(token, {});
  return genBreadcrumbStyle(breadcrumbToken);
}, prepareComponentToken);