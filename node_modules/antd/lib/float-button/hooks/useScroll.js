"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _react = _interopRequireDefault(require("react"));
var _getScroll = _interopRequireDefault(require("../../_util/getScroll"));
var _is = require("../../_util/is");
var _throttleByAnimationFrame = _interopRequireDefault(require("../../_util/throttleByAnimationFrame"));
const getScrollProgress = target => {
  const scrollTop = (0, _getScroll.default)(target);
  let scrollElement = null;
  if ((0, _is.isWindow)(target)) {
    scrollElement = target.document.documentElement;
  } else if ((0, _is.isDocument)(target)) {
    scrollElement = target.documentElement;
  } else if ((0, _is.isHTMLElement)(target)) {
    scrollElement = target;
  }
  if (!scrollElement) {
    return 0;
  }
  const maxScroll = Math.max(scrollElement.scrollHeight - scrollElement.clientHeight, 0);
  return maxScroll > 0 ? Math.min(Math.max(scrollTop / maxScroll, 0), 1) : 0;
};
const useScroll = options => {
  const {
    getTarget,
    showProgress,
    visibilityHeight
  } = options;
  const [visible, setVisible] = _react.default.useState(visibilityHeight === 0);
  const [scrollProgress, setScrollProgress] = _react.default.useState(0);
  _react.default.useEffect(() => {
    const container = getTarget();
    const syncScrollState = () => {
      setVisible((0, _getScroll.default)(container) >= visibilityHeight);
      if (showProgress) {
        setScrollProgress(getScrollProgress(container));
      }
    };
    const handleScroll = (0, _throttleByAnimationFrame.default)(syncScrollState);
    syncScrollState();
    container?.addEventListener('scroll', handleScroll);
    return () => {
      handleScroll.cancel();
      container?.removeEventListener('scroll', handleScroll);
    };
  }, [getTarget, showProgress, visibilityHeight]);
  _react.default.useEffect(() => {
    if (!showProgress) {
      return;
    }
    const handleResize = (0, _throttleByAnimationFrame.default)(() => {
      setScrollProgress(getScrollProgress(getTarget()));
    });
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      handleResize.cancel();
    };
  }, [getTarget, showProgress]);
  return {
    scrollProgress,
    visible
  };
};
var _default = exports.default = useScroll;