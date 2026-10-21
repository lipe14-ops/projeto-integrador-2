"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _cssinjs = require("@ant-design/cssinjs");
var _motion = require("../../style/motion");
var _internal = require("../../theme/internal");
var _genStyleUtils = require("../../theme/util/genStyleUtils");
var _util = require("../util");
// =========================== Animation ============================
const antBorderBeamMove = new _cssinjs.Keyframes('antBorderBeamMove', {
  from: {
    offsetDistance: '0%'
  },
  to: {
    offsetDistance: '100%'
  }
});
const genBorderBeamStyle = token => {
  const {
    componentCls,
    antCls,
    colorPrimary,
    colorPrimaryHover,
    lineWidth
  } = token;
  const [, varRef] = (0, _genStyleUtils.genCssVar)(antCls, 'border-beam');
  const defaultBeamGradient = `linear-gradient(to left, ${colorPrimary} 0%, ${colorPrimaryHover} ${_util.MAX_BEAM_COLOR_STOP_PERCENT}%, transparent)`;
  // ============================= Style ==============================
  return {
    [componentCls]: {
      // Container
      display: 'none',
      position: 'absolute',
      inset: varRef('inset-offset', '0px'),
      borderRadius: 'inherit',
      zIndex: 1,
      overflow: 'hidden',
      pointerEvents: 'none',
      // Border Beam
      padding: varRef('line-width', (0, _cssinjs.unit)(lineWidth)),
      // Border Beam Effect
      '@supports ((mask-composite: exclude) or (-webkit-mask-composite: xor))': {
        WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        WebkitMaskComposite: 'xor',
        mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        maskComposite: 'exclude',
        '@supports (offset-path: rect(0 auto auto 0 round 1px))': {
          display: 'block',
          '&::before': {
            ...(0, _motion.genNoMotionRawStyle)(),
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            width: varRef('size', '100px'),
            aspectRatio: '1 / 1',
            opacity: 0.95,
            backgroundImage: varRef('beam-gradient', defaultBeamGradient),
            offsetAnchor: '90% 50%',
            offsetDistance: '0%',
            offsetPath: `rect(0 auto auto 0 round ${varRef('size', '100px')})`,
            offsetRotate: 'auto',
            animationName: antBorderBeamMove,
            animationDuration: varRef('duration', `${_util.DEFAULT_BORDER_BEAM_DURATION}s`),
            animationDelay: varRef('delay', '0s'),
            animationTimingFunction: 'linear',
            animationIterationCount: 'infinite',
            willChange: 'offset-distance'
          }
        }
      },
      '@media (prefers-reduced-motion: reduce)': {
        '&::before': {
          display: 'none'
        }
      }
    }
  };
};
var _default = exports.default = (0, _internal.genStyleHooks)('BorderBeam', genBorderBeamStyle);